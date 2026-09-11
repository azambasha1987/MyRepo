# PNetLab Artifacts & Releases Verification Report

Last updated: 2026-09-11 02:18:33 UTC

## Step 1: Git Repository Verification

- **Remote URL**: `https://codeberg.org/netkillui/Pnetlabv8.git`
- **Local Clone Path**: [`track-1-git/`](file:///e:/Git/EMULATOR/0-P-UNTOUCHED/track-1-git)
- **Branch**: `main`

## Step 2: Codeberg Package API Releases Verification

- **Package Registry API**: `https://codeberg.org/api/v1/packages/netkillui`
- **Debian APT Repository**: `https://codeberg.org/api/packages/netkillui/debian` (dist: `resolute`, component: `main`)

### Verified File Manifest

| Category | Local Path | Size (bytes) | Status | SHA256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| Debian (pnetlab-bridge-dkms v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-bridge-dkms_6.8.78resolute1_all.deb` | 142,698 | ✅ VERIFIED | `8066b5796736d4c1c423be392867cb6142080cf6bfd5f4e4967e12469f7e7cb7` |
| Debian (pnetlab-docker v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-docker_6.8.78resolute1_amd64.deb` | 3,618 | ✅ VERIFIED | `ff6609c4bdefcce6c4962a8f25e4b06fa2dbcf8e027b47a6d84f2fa0bfea64a7` |
| Debian (pnetlab-guacd v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-guacd_6.8.78resolute1_amd64.deb` | 463,070 | ✅ VERIFIED | `ba7435f00e015efd828cef8eedfb050fbd20261c0a91f4b8ccd284232b37fe10` |
| Debian (pnetlab-qemu v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-qemu_6.8.78resolute1_amd64.deb` | 1,275,462 | ✅ VERIFIED | `382da8190a386e3984855f0aaa96ecb5f32a2ff53993eac824a33434ef4920bc` |
| Debian (pnetlab-satellite v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-satellite_6.8.78resolute1_amd64.deb` | 82,378,066 | ✅ VERIFIED | `bc7422cf64f2fdee24302cb3b0a5f170679caf27a64ecc18e98a190432bfd596` |
| Debian (pnetlab-schema v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-schema_6.8.78resolute1_amd64.deb` | 9,066 | ✅ VERIFIED | `8b55771279f3cfbe132b658ca331ca9d40161021456f7a435f153f80a85825fc` |
| Debian (pnetlab-vpcs v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-vpcs_6.8.78resolute1_amd64.deb` | 90,288 | ✅ VERIFIED | `4fff6ca5c74c11a09566e6c4d7ada2c81bf847f2daf38d33b7a83a57f8131734` |
| Debian (pnetlab v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab_6.8.78resolute1_amd64.deb` | 87,935,844 | ✅ VERIFIED | `088426541ac429a19e9417655b7570773d55c776caa7fd6afc0c209d88af974d` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-latest.json` | 205 | ✅ VERIFIED | `dfc833d5811ce58fcbdf6d170722f961e6126e707b8bbca252062e111d4cb649` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-latest.json.sha256` | 86 | ✅ VERIFIED | `13fbcdf5e7ea5e4f1c20f2af46f12f458f9d0966b851344b9f3a81bab67a856c` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-latest.json.sig` | 566 | ✅ VERIFIED | `a30deafa17c364cb8f6a11b7db6772d326b12aa6838f9a80d5356cfb4ff125e2` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-network-install-latest.sh` | 174,477 | ✅ VERIFIED | `6f9b3c24d4975a60e3cc64aa11cc0c60d83699e4938bee340953c52549242262` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-network-install-latest.sh.sha256` | 100 | ✅ VERIFIED | `6ba4056de4ea3205b57544dd55d9621f7ca24bdd4d7c853a71b8741eaa0e0fd4` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-6.8.78resolute1-manifest.json` | 1,513 | ✅ VERIFIED | `289945b0ea1e6d364d5c892f17945ec4ac5e042b57b65724d250329b5950f8c3` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-6.8.78resolute1-manifest.json.sha256` | 104 | ✅ VERIFIED | `9116ee0c92b6b887d1f0702cbdfe909b366200f88b2391623f04facfa8e09d1d` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-6.8.78resolute1-manifest.json.sig` | 566 | ✅ VERIFIED | `c9edd0841291e89d552bba94f52cebcbac697f6888a85bd34fa0d0e8a20c0f93` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-core-assets-6.8.78resolute1.tar.zst` | 75,116,436 | ✅ VERIFIED | `b36bc01d72c33e69d97122e37f25eaf58476ae7d1af442a9473c1f42a2a1ad9d` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-core-assets-6.8.78resolute1.tar.zst.sha256` | 110 | ✅ VERIFIED | `8fa2dfefa428f23f9870208fbe63ff85f1d32904de13225a7873c6c4e61251f2` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-core-assets-6.8.78resolute1.tar.zst.sig` | 566 | ✅ VERIFIED | `f12e2ba56387cd912a7f9f39366311111d2e9f86f80e7f4c58985620ffcfc147` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-install-resolute-satellite-6.8.78resolute1.sh` | 15,185 | ✅ VERIFIED | `6e6469593a7a42519939b076cfed55ea3017fc107e38db0d7080d96674e4c751` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-install-resolute-satellite-6.8.78resolute1.sh.sha256` | 120 | ✅ VERIFIED | `0c5f90aaa405fcf7ce10f0b4c4deb9bb8874a5d5f18d44ed84c9e64668e778f7` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-network-install-6.8.78resolute1.sh` | 174,477 | ✅ VERIFIED | `6f9b3c24d4975a60e3cc64aa11cc0c60d83699e4938bee340953c52549242262` |
| Generic (pnetlab-core-assets @ 6.8.78resolute1) | `generic/6.8.78resolute1/pnetlab-network-install-6.8.78resolute1.sh.sha256` | 109 | ✅ VERIFIED | `d5ed2df532044db23eabe96e603d77cf8840db86da70a02f9da73d2412b2f89f` |
| Metadata Index | `metadata/binary-all-Packages` | 1,827 | ✅ VERIFIED | `82506a4a13ebef4f6a39d8bb0187e900e74e36754b8a1e46ab921bf358373a2e` |
| Metadata Index | `metadata/binary-amd64-Packages` | 13,929 | ✅ VERIFIED | `9aeb5f60de1d80149f6cb617c487dfaa3565eb07b7c9ee028357d0733a09b33f` |
| Metadata Index | `metadata/dists-resolute-Release` | 2,633 | ✅ VERIFIED | `980a33708633f809684a4aec7b010b3538330ad38236961e592993652469e761` |
| Metadata Index | `metadata/generic-package-details.json` | 7,232 | ✅ VERIFIED | `155dc1db403babc826f9ce3d49e136efd7d5ffc5951b825a63297038ad249556` |
| Metadata Index | `metadata/packages-api-response.json` | 18,496 | ✅ VERIFIED | `7b7d0dda21c9ef8c22861314ee45fa364298d87a21e04981d4d9c140c703f427` |
