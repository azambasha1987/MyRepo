# AzamLabs

AzamLabs is a self-hosted virtual network emulation platform and enterprise network automation repository. It brings together high-performance network device virtualization and modern NetDevOps toolchains into an integrated engineering ecosystem.

---

## Repository Structure

This repository is organized into two core modules:

* **[`AzamLabs/`](AzamLabs/)**: The standalone network emulation platform engine, web management interfaces, high-density hypervisor configurations, and system operations toolchains.
* **[`IT-AUTOMATION/`](IT-AUTOMATION/)**: Enterprise network automation workflows, Ansible playbooks, and multi-vendor automation scripts (Netmiko, Paramiko, NAPALM) targeting Cisco, Arista, and Linux network topologies.

---

## Platform Highlights

### Standalone Multi-Vendor Network Emulation
* **Wide Virtual Device Ecosystem**: Native support for Cisco IOL, QEMU/KVM virtual appliances (IOS-XE, IOS-XR, NX-OS), containerized network functions (Docker/Containerlab), and standard Linux end-host micro-appliances.
* **Accelerated Dataplane Engine**: Kernel-level fast-path bridge acceleration delivering high throughput and low-latency link interconnection between simulated nodes.
* **Resource Optimization & Density**: Adaptive CPU governors, Kernel Same-page Merging (KSM), and boot-storm dampening for scaling large multi-node topologies on resource-constrained hardware.

### Intelligent Canvas & Visual Toolkit
* **Smart Alignment Dock**: Precision layout tools including horizontal/vertical distribution, grid snapping, radial alignment, and node centering.
* **Spotlight Quick-Switcher**: Keyboard-driven quick-access command palette for searching devices, executing operations, and switching active viewports.
* **Radar Mini-Map**: Dynamic floating canvas navigator providing real-time panning across sprawling multi-tier network topologies.
* **Live In-Browser Packet Dissector**: Capture and inspect data packets directly in the web browser without requiring external client software installations.

### Enterprise Cluster Architecture
* **Master-Satellite Scaling**: Scale compute workloads seamlessly across multiple physical hypervisors by attaching headless worker nodes to an active master cluster.
* **Automated SSL & Security**: Built-in TLS certificate provisioning, local CA authority generation, and trusted browser integration.
* **Automated Backups & Versioning**: Complete lab topology state snapshots, configuration diffs, and Git-backed topology version tracking.

---

## Network Automation Suites

The [`IT-AUTOMATION/`](IT-AUTOMATION/) module provides tested production-grade automation scripts designed to interact directly with network nodes running in AzamLabs or physical environments:

* **Ansible Workflows**: Playbooks and roles for structured multi-device configuration provisioning and compliance auditing.
* **Python Network Libraries**: Netmiko, Paramiko, and NAPALM automation scripts for device scraping, zero-touch configuration backups, BGP policy enforcement, and dynamic interface provisioning.
