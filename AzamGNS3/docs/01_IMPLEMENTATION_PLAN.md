# 01. Implementation Plan & Acquisition Record

## 1. Objective
Establish a clean, reproducible, and maintainable copy of the official **GNS3** source code under `e:\Git\AzamGNS3` to serve as the foundation for the high-performance, web-native platform.

---

## 2. Decision Log

| Decision Parameter | User Choice | Justification |
| :--- | :--- | :--- |
| **Component Scope (Decision A)** | **Option A1: All Core Components** | Incorporates backend daemon (`gns3-server`), desktop client (`gns3-gui`), and web UI (`gns3-web-ui`). |
| **Branch / Target (Decision B)** | **Bleeding Edge (`master` branch)** | Targets the latest active upstream commits with support for modern dependencies and features. |
| **Repository Topology (Decision C)** | **Git Submodules** | Tracks official GNS3 upstream repositories cleanly inside `MyRepo` without untracked git-in-git conflicts. |

---

## 3. Repositories Pinned

| Component | Path | Upstream Remote | Branch | Commit SHA |
| :--- | :--- | :--- | :--- | :--- |
| **GNS3 Server** | [`AzamGNS3/gns3-server`](file:///e:/Git/AzamGNS3/gns3-server) | `https://github.com/GNS3/gns3-server.git` | `master` | `a3e85b70` |
| **GNS3 GUI** | [`AzamGNS3/gns3-gui`](file:///e:/Git/AzamGNS3/gns3-gui) | `https://github.com/GNS3/gns3-gui.git` | `master` | `c776d4ef` |
| **GNS3 Web UI** | [`AzamGNS3/gns3-web-ui`](file:///e:/Git/AzamGNS3/gns3-web-ui) | `https://github.com/GNS3/gns3-web-ui.git` | `master` | `800bcfb2` |

---

## 4. Submodule Setup Record
Executed from repository root:
```powershell
git submodule add -b master https://github.com/GNS3/gns3-server.git AzamGNS3/gns3-server
git submodule add -b master https://github.com/GNS3/gns3-gui.git AzamGNS3/gns3-gui
git submodule add -b master https://github.com/GNS3/gns3-web-ui.git AzamGNS3/gns3-web-ui
```
Recorded in parent `.gitmodules` and committed under SHA `a090576`.
