import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from azamlabs.config import settings
from azamlabs.core.schema import AzamTopology, AzamNode
from azamlabs.core.engine import engine
from azamlabs.core.day0 import Day0ConfigGenerator
from azamlabs.core.ksm import KsmManager
from azamlabs.core.cluster import cluster_manager
from azamlabs.core.watchdog import watchdog
from azamlabs.converters.universal import UniversalConverter
from azamlabs.console.gateway import gateway
from azamlabs.console.paster import flow_paster
from azamlabs.console.uris import launcher_manager
from azamlabs.mcp.server import mcp_server
from azamlabs.auth.router import auth_router
from azamlabs.core.folders import folder_service
from azamlabs.converters.batch import BatchLabImporter


class ImportLabRequest(BaseModel):
    content: str
    filename: Optional[str] = None
    format_hint: Optional[str] = None


class BatchImportRequest(BaseModel):
    source_path: str
    target_folder: Optional[str] = None
    dry_run: bool = False


class CloneLabRequest(BaseModel):
    new_name: Optional[str] = None


class PasteConfigRequest(BaseModel):
    config_text: str
    inter_line_delay_ms: int = 50
    stop_on_error: bool = False


class CreateFolderRequest(BaseModel):
    name: str
    parent_id: Optional[str] = "root"


class MoveLabRequest(BaseModel):
    folder_path: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts background watchdog and registers system services."""
    await watchdog.start()
    yield
    """Gracefully shuts down background watchdog."""
    await watchdog.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AzamLabs Universal Network, Cloud & Cybersecurity Emulation Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for local Studio frontend and external dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Authentication Router
app.include_router(auth_router)


@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Returns real-time health, platform version, and KSM status."""
    return {
        "status": "online",
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "ksm_telemetry": KsmManager.get_telemetry(),
    }


# ==========================================
# Lab Lifecycle Endpoints
# ==========================================

@app.post("/api/v1/labs", response_model=AzamTopology, tags=["Labs"])
async def create_lab(topology: AzamTopology) -> AzamTopology:
    """Creates and persists a new lab topology."""
    try:
        return engine.create_lab(topology)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/labs", response_model=List[Dict[str, Any]], tags=["Labs"])
async def list_labs() -> List[Dict[str, Any]]:
    """Returns a list of all stored lab topologies with summary metrics."""
    return engine.list_labs()


@app.get("/api/v1/labs/{lab_id}", response_model=AzamTopology, tags=["Labs"])
async def get_lab(lab_id: str) -> AzamTopology:
    """Retrieves full topology definition and live node states."""
    topo = engine.get_lab(lab_id)
    if not topo:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")
    return topo


@app.delete("/api/v1/labs/{lab_id}", tags=["Labs"])
async def delete_lab(lab_id: str) -> Dict[str, Any]:
    """Tears down and deletes a lab."""
    deleted = await engine.delete_lab(lab_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")
    return {"status": "deleted", "lab_id": lab_id}


@app.post("/api/v1/labs/{lab_id}/start", tags=["Lifecycle"])
async def start_all_nodes(lab_id: str) -> Dict[str, Any]:
    """Starts all nodes in a lab using anti-bootstorm staggered scheduling."""
    try:
        results = await engine.start_all_nodes(lab_id)
        return {"status": "started", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/labs/{lab_id}/stop", tags=["Lifecycle"])
async def stop_all_nodes(lab_id: str) -> Dict[str, Any]:
    """Stops all running nodes in a lab."""
    results = await engine.stop_all_nodes(lab_id)
    return {"status": "stopped", "results": results}


@app.post("/api/v1/labs/{lab_id}/wipe", tags=["Lifecycle"])
async def wipe_all_nodes(lab_id: str) -> Dict[str, Any]:
    """Wipes all ephemeral overlays and resets the lab to Day-0."""
    await engine.wipe_all_nodes(lab_id)
    return {"status": "wiped", "lab_id": lab_id}


@app.get("/api/v1/labs/{lab_id}/status", tags=["Lifecycle"])
async def get_lab_status(lab_id: str) -> Dict[str, Any]:
    """Returns comprehensive real-time status and telemetry for a lab."""
    try:
        return engine.get_lab_status(lab_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# Folder-Wise Lab Hierarchy Endpoints
# ==========================================

@app.get("/api/v1/folders", tags=["Folders"])
async def get_folder_tree() -> List[Dict[str, Any]]:
    """Returns structured folder tree with labs nested under each folder."""
    return folder_service.get_folder_tree()


@app.post("/api/v1/folders", tags=["Folders"])
async def create_folder_endpoint(request: CreateFolderRequest) -> Dict[str, Any]:
    """Creates a new folder in the hierarchy."""
    return folder_service.create_folder(name=request.name, parent_id=request.parent_id)


@app.delete("/api/v1/folders/{folder_id}", tags=["Folders"])
async def delete_folder_endpoint(folder_id: str, delete_contents: bool = False) -> Dict[str, Any]:
    """Deletes a folder. If delete_contents=true, deletes all nested labs; otherwise moves them to root."""
    success = folder_service.delete_folder(folder_id, delete_contents=delete_contents)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete root folder or folder not found.")
    return {"status": "deleted", "folder_id": folder_id, "cascaded": delete_contents}


@app.get("/api/v1/folders/{folder_id}/export", tags=["Folders"])
async def export_folder_zip_endpoint(folder_id: str):
    """Exports all labs in a folder tree into a downloadable ZIP archive."""
    try:
        zip_bytes = folder_service.export_folder_zip(folder_id)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=folder_{folder_id}_export.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/v1/labs/{lab_id}/move", tags=["Folders"])
async def move_lab_endpoint(lab_id: str, request: MoveLabRequest) -> Dict[str, Any]:
    """Moves a lab topology to target folder path."""
    success = folder_service.move_lab(lab_id, request.folder_path)
    if not success:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")
    return {"status": "moved", "lab_id": lab_id, "folder_path": request.folder_path}


@app.post("/api/v1/labs/{lab_id}/clone", tags=["Labs"])
async def clone_lab_endpoint(lab_id: str, request: Optional[CloneLabRequest] = None) -> Dict[str, Any]:
    """Duplicates an existing lab into a new independent topology."""
    new_name = request.new_name if request else None
    cloned = folder_service.duplicate_lab(lab_id, new_name=new_name)
    if not cloned:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")
    return cloned



# ==========================================
# Individual Node Control
# ==========================================

@app.post("/api/v1/labs/{lab_id}/nodes/{node_id}/start", tags=["Nodes"])
async def start_single_node(lab_id: str, node_id: str) -> Dict[str, Any]:
    """Starts a specific node."""
    try:
        success = await engine.start_node(lab_id, node_id)
        return {"node_id": node_id, "started": success}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/v1/labs/{lab_id}/nodes/{node_id}/stop", tags=["Nodes"])
async def stop_single_node(lab_id: str, node_id: str) -> Dict[str, Any]:
    """Stops a specific node."""
    try:
        success = await engine.stop_node(lab_id, node_id)
        return {"node_id": node_id, "stopped": success}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# Day-0 Automation & Cluster Endpoints
# ==========================================

@app.post("/api/v1/labs/{lab_id}/day0", tags=["Automation"])
async def generate_day0_configs(lab_id: str, routing: str = "ospf") -> Dict[str, str]:
    """Generates Day-0 IP planning and initial configurations for all nodes."""
    topo = engine.get_lab(lab_id)
    if not topo:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")

    Day0ConfigGenerator.auto_assign_ip_plan(topo)
    configs = {}
    for node in topo.nodes:
        cfg = Day0ConfigGenerator.generate_config(node, topo, routing_protocol=routing)
        node.startup_config = cfg
        configs[node.name] = cfg

    engine.create_lab(topo)  # Save updated IP plans and configs
    return configs


@app.get("/api/v1/cluster/satellites", tags=["Cluster"])
async def list_cluster_satellites() -> List[Any]:
    """Lists registered cluster satellite compute nodes."""
    return cluster_manager.list_satellites()


# ==========================================
# Universal Multi-Platform Converters
# ==========================================

@app.post("/api/v1/convert/import", response_model=AzamTopology, tags=["Converters"])
async def import_lab_payload(request: ImportLabRequest) -> AzamTopology:
    """Auto-detects and converts raw string payload (CLAB, CML, EVE, GNS3, P2V) into AzamTopology."""
    try:
        topo = UniversalConverter.import_lab(
            content=request.content,
            filename=request.filename,
            format_hint=request.format_hint
        )
        return engine.create_lab(topo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Conversion error: {str(e)}")


@app.post("/api/v1/convert/upload", tags=["Converters"])
async def upload_and_import_lab(file: UploadFile = File(...)):
    """Uploads any lab file (*.clab.yml, *.yaml, *.unl, *.gns3, *.gns3project, *.azaml, *.zip, *.cfg) and imports it."""
    try:
        content_bytes = await file.read()
        filename_lower = (file.filename or "").lower()

        if filename_lower.endswith(".zip"):
            # Batch import archive
            return BatchLabImporter.import_zip(content_bytes, dry_run=False)

        topo = UniversalConverter.import_lab(
            content=content_bytes,
            filename=file.filename
        )
        return engine.create_lab(topo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import uploaded file: {str(e)}")


@app.post("/api/v1/convert/upload-archive", tags=["Converters"])
async def upload_archive_endpoint(
    file: UploadFile = File(...),
    target_folder: Optional[str] = Form(None),
    dry_run: bool = Form(False)
) -> Dict[str, Any]:
    """Uploads a ZIP archive of labs, extracting and importing all topologies."""
    try:
        content = await file.read()
        return BatchLabImporter.import_zip(
            zip_source=content,
            target_folder=target_folder,
            dry_run=dry_run
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Archive import failed: {str(e)}")


@app.post("/api/v1/convert/batch-import", tags=["Converters"])
async def batch_import_endpoint(request: BatchImportRequest) -> Dict[str, Any]:
    """Batch imports topologies from a local directory or ZIP file on the host machine."""
    path = Path(request.source_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path '{request.source_path}' does not exist.")

    try:
        if path.is_file() and path.suffix.lower() == ".zip":
            return BatchLabImporter.import_zip(
                zip_source=path,
                target_folder=request.target_folder,
                dry_run=request.dry_run
            )
        elif path.is_dir():
            return BatchLabImporter.import_directory(
                dir_path=path,
                target_folder=request.target_folder,
                dry_run=request.dry_run
            )
        else:
            raise HTTPException(status_code=400, detail="source_path must be a .zip archive or a directory.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Batch import failed: {str(e)}")


@app.get("/api/v1/convert/export/{lab_id}/{target_format}", tags=["Converters"])
async def export_lab_endpoint(lab_id: str, target_format: str):
    """Exports an existing lab topology to any target format (clab, cml, eve, gns3, azaml, yaml)."""
    topo = engine.get_lab(lab_id)
    if not topo:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")
    try:
        exported = UniversalConverter.export_lab(topo, target_format)
        if isinstance(exported, bytes):
            return Response(
                content=exported,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={topo.name.replace(' ', '_')}.{target_format}"}
            )
        return Response(
            content=exported,
            media_type="text/plain",
            headers={"Content-Disposition": f"inline; filename={topo.name.replace(' ', '_')}.{target_format}"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Export error: {str(e)}")


# ==========================================
# WebSockets Telemetry Stream
# ==========================================

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Streams real-time CPU, RAM, and KSM telemetry to AzamLabs Studio."""
    await websocket.accept()
    try:
        while True:
            data = {
                "ksm": KsmManager.get_telemetry(),
                "cluster_nodes": len(cluster_manager.list_satellites()),
                "total_labs": len(engine.list_labs()),
            }
            await websocket.send_json(data)
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        pass


# ==========================================
# Multi-Protocol Web Terminal & Console
# ==========================================

@app.websocket("/ws/console/{lab_id}/{node_id}")
async def websocket_console_endpoint(websocket: WebSocket, lab_id: str, node_id: str):
    """Bridges xterm.js Web Terminal directly to the node serial/telnet console socket."""
    await gateway.bridge_websocket_to_tcp(websocket, lab_id, node_id)


@app.post("/api/v1/console/{lab_id}/{node_id}/paste", tags=["Console"])
async def paste_configuration_endpoint(
    lab_id: str,
    node_id: str,
    request: PasteConfigRequest
) -> Dict[str, Any]:
    """Injects bulk configuration into node with flow control, pacing, and syntax checking."""
    topo = engine.get_lab(lab_id)
    if not topo:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")
    node = topo.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
    if not node.console_port:
        raise HTTPException(status_code=400, detail=f"Node '{node.name}' has no active console port.")

    results = await flow_paster.paste_configuration(
        host="127.0.0.1",
        port=node.console_port,
        config_text=request.config_text,
        inter_line_delay_ms=request.inter_line_delay_ms,
        stop_on_error=request.stop_on_error,
    )
    return results


@app.get("/api/v1/console/{lab_id}/{node_id}/uri", tags=["Console"])
async def get_node_uri_endpoint(lab_id: str, node_id: str) -> Dict[str, str]:
    """Returns desktop native URI scheme (e.g. telnet://127.0.0.1:32768)."""
    topo = engine.get_lab(lab_id)
    if not topo:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")
    node = topo.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    uri = launcher_manager.get_node_uri(node)
    return {"node_name": node.name, "uri": uri, "port": str(node.console_port or 23)}


@app.get("/api/v1/console/{lab_id}/launcher/{client_app}", tags=["Console"])
async def download_terminal_launcher(lab_id: str, client_app: str):
    """Downloads 1-click batch launcher script for SecureCRT, PuTTY, Windows Terminal, or iTerm2."""
    topo = engine.get_lab(lab_id)
    if not topo:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found.")

    app_type = client_app.lower()
    if app_type in ("wt", "windowsterminal", "windows_terminal"):
        script = launcher_manager.generate_windows_terminal_script(topo.name, topo.nodes)
        filename = f"launch_{topo.name.replace(' ', '_')}_wt.bat"
    elif app_type in ("securecrt", "crt"):
        script = launcher_manager.generate_securecrt_script(topo.name, topo.nodes)
        filename = f"launch_{topo.name.replace(' ', '_')}_securecrt.vbs"
    elif app_type in ("putty", "kitty"):
        script = launcher_manager.generate_putty_batch_script(topo.name, topo.nodes)
        filename = f"launch_{topo.name.replace(' ', '_')}_putty.bat"
    elif app_type in ("iterm2", "mac", "iterm"):
        script = launcher_manager.generate_iterm2_script(topo.name, topo.nodes)
        filename = f"launch_{topo.name.replace(' ', '_')}_iterm2.scpt"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported terminal client '{client_app}'. Use: wt, securecrt, putty, iterm2")

    return Response(
        content=script,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==========================================
# Model Context Protocol (MCP) Server
# ==========================================

@app.post("/mcp", tags=["MCP"])
async def mcp_json_rpc_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-RPC 2.0 Model Context Protocol endpoint for external AI assistants (Claude, Gemini, Antigravity)."""
    return await mcp_server.process_json_rpc(payload)


# ==========================================
# Frontend Static Files Mount
# ==========================================
frontend_dir = settings.STATIC_DIR
if not frontend_dir.exists():
    for candidate in [
        Path("/opt/azamlabs/frontend"),
        Path.cwd() / "frontend",
        Path(__file__).resolve().parent.parent.parent / "frontend",
    ]:
        if candidate.exists():
            frontend_dir = candidate
            break

if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

