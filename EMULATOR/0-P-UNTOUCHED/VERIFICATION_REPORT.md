# PNetLab Artifacts & Releases Verification Report

Last updated: 2026-09-18 02:29:48 UTC

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
| Debian (pnetlab-bridge-dkms v6.8.79resolute1) | `debian/pool/resolute/main/pnetlab-bridge-dkms_6.8.79resolute1_all.deb` | 142,686 | ✅ VERIFIED | `f93c80e78df04ddcd77dcaed417fce5f6982a8f2175a27fa7ef0d49a55f26300` |
| Debian (pnetlab-docker v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-docker_6.8.78resolute1_amd64.deb` | 3,618 | ✅ VERIFIED | `ff6609c4bdefcce6c4962a8f25e4b06fa2dbcf8e027b47a6d84f2fa0bfea64a7` |
| Debian (pnetlab-docker v6.8.79resolute1) | `debian/pool/resolute/main/pnetlab-docker_6.8.79resolute1_amd64.deb` | 3,616 | ✅ VERIFIED | `a825c368a569f749f80e93d37216d6e7104133b85c79865c15600ad8deaa049b` |
| Debian (pnetlab-guacd v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-guacd_6.8.78resolute1_amd64.deb` | 463,070 | ✅ VERIFIED | `ba7435f00e015efd828cef8eedfb050fbd20261c0a91f4b8ccd284232b37fe10` |
| Debian (pnetlab-guacd v6.8.79resolute1) | `debian/pool/resolute/main/pnetlab-guacd_6.8.79resolute1_amd64.deb` | 463,132 | ✅ VERIFIED | `8348f84d756273b592ec1ce184c2be573607086d3baf07a66d9cf06e31bd3455` |
| Debian (pnetlab-qemu v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-qemu_6.8.78resolute1_amd64.deb` | 1,275,462 | ✅ VERIFIED | `382da8190a386e3984855f0aaa96ecb5f32a2ff53993eac824a33434ef4920bc` |
| Debian (pnetlab-qemu v6.8.79resolute1) | `debian/pool/resolute/main/pnetlab-qemu_6.8.79resolute1_amd64.deb` | 1,275,538 | ✅ VERIFIED | `03090de077cd596318b55b3c47eb7f9030beffd7b89a6b59105eecca45ea3a7c` |
| Debian (pnetlab-satellite v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-satellite_6.8.78resolute1_amd64.deb` | 82,378,066 | ✅ VERIFIED | `bc7422cf64f2fdee24302cb3b0a5f170679caf27a64ecc18e98a190432bfd596` |
| Debian (pnetlab-satellite v6.8.79resolute1) | `debian/pool/resolute/main/pnetlab-satellite_6.8.79resolute1_amd64.deb` | 9,981,780 | ✅ VERIFIED | `02fb08c36d030c6b03ef67e2da1ae5563c027605605ec271fa13985f7e4c3870` |
| Debian (pnetlab-schema v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-schema_6.8.78resolute1_amd64.deb` | 9,066 | ✅ VERIFIED | `8b55771279f3cfbe132b658ca331ca9d40161021456f7a435f153f80a85825fc` |
| Debian (pnetlab-schema v6.8.79resolute1) | `debian/pool/resolute/main/pnetlab-schema_6.8.79resolute1_amd64.deb` | 9,104 | ✅ VERIFIED | `be1c7cd96670e664ce48b3ac8a1b7cf31e33a9db9163080d2060630369ff3527` |
| Debian (pnetlab-vpcs v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab-vpcs_6.8.78resolute1_amd64.deb` | 90,288 | ✅ VERIFIED | `4fff6ca5c74c11a09566e6c4d7ada2c81bf847f2daf38d33b7a83a57f8131734` |
| Debian (pnetlab-vpcs v6.8.79resolute1) | `debian/pool/resolute/main/pnetlab-vpcs_6.8.79resolute1_amd64.deb` | 90,324 | ✅ VERIFIED | `6d986a6b4c8cedfb38fdc7d8a9305f87b7bf5c26dd6eb9ffdd6dac1c270dc214` |
| Debian (pnetlab v6.8.78resolute1) | `debian/pool/resolute/main/pnetlab_6.8.78resolute1_amd64.deb` | 87,935,844 | ✅ VERIFIED | `088426541ac429a19e9417655b7570773d55c776caa7fd6afc0c209d88af974d` |
| Debian (pnetlab v6.8.79resolute1) | `debian/pool/resolute/main/pnetlab_6.8.79resolute1_amd64.deb` | 15,536,812 | ✅ VERIFIED | `543ec692ef4b5e95520424bf03c9eaebbdb6fc5cbe19e861db12a9e182a3274e` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-latest.json` | 205 | ✅ VERIFIED | `5d00a5812b0def440421bf997498ca61d6e9ca1f04d89deea5276506ba30b764` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-latest.json.sha256` | 86 | ✅ VERIFIED | `2d1c07365968cc2901b4acdce5df36b39ebc7485cf406b4cf1076f3e61c7ba25` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-latest.json.sig` | 566 | ✅ VERIFIED | `d0d37b3ef6aa36b42c87a5f36d5b6650ebf92ac75bcdcd144e59aa9434f9571c` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-network-install-latest.sh` | 176,628 | ✅ VERIFIED | `b6b3c8b0e81f1a2ac2b2d1af37f4261ec76d5bfd8e9c98045390137efb74f37a` |
| Generic (pnetlab-core-assets @ 0.channel) | `generic/0.channel/pnetlab-network-install-latest.sh.sha256` | 100 | ✅ VERIFIED | `c09eccbaf0b0e4c922e4fc38a0675cd47a98f0771ba257ef56bb77bb66c13dd2` |
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
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-6.8.79resolute1-manifest.json` | 1,826 | ✅ VERIFIED | `bbf5879a4506d78f458cdfb9b8560075b6b65822515e546fab31b0bdc3371629` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-6.8.79resolute1-manifest.json.sha256` | 104 | ✅ VERIFIED | `fd7c469cc3b9b2c12c19567fddf68e49ffa2293ee1d6f445667c9182bd7bd75e` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-6.8.79resolute1-manifest.json.sig` | 566 | ✅ VERIFIED | `91f21ce160d3ed5a793f8dab8ef5c133b0d6d429177746d3067e8031c0ab3197` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-core-assets-6.8.79resolute1.tar.zst` | 75,116,436 | ✅ VERIFIED | `b36bc01d72c33e69d97122e37f25eaf58476ae7d1af442a9473c1f42a2a1ad9d` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-core-assets-6.8.79resolute1.tar.zst.sha256` | 110 | ✅ VERIFIED | `3a5dbb5a347a9f5e07263ee40a0a8017fe7afeea3eb52b4581ed1754700cb43a` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-core-assets-6.8.79resolute1.tar.zst.sig` | 566 | ✅ VERIFIED | `691e7b08153f8dc1972ad9e9af03535aa97021c20e2eb6497b3357a4938b2326` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-install-resolute-satellite-6.8.79resolute1.sh` | 15,185 | ✅ VERIFIED | `6e6469593a7a42519939b076cfed55ea3017fc107e38db0d7080d96674e4c751` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-install-resolute-satellite-6.8.79resolute1.sh.sha256` | 120 | ✅ VERIFIED | `c99831f9cf7c4e35bd3028c01aadc38c170d34adeebbe4f4a510d822976875e5` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-network-install-6.8.79resolute1.sh` | 176,628 | ✅ VERIFIED | `b6b3c8b0e81f1a2ac2b2d1af37f4261ec76d5bfd8e9c98045390137efb74f37a` |
| Generic (pnetlab-core-assets @ 6.8.79resolute1) | `generic/6.8.79resolute1/pnetlab-network-install-6.8.79resolute1.sh.sha256` | 109 | ✅ VERIFIED | `4f4cd8d193f939cf0e6e37481c2d964b517f47085f45e54364b25c39ade436db` |
| Metadata Index | `metadata/binary-all-Packages` | 3,655 | ✅ VERIFIED | `2eb2d96e45eb225184b796e18b3a33ce0bb309f2214d2ef7d8395b96dae4d9fd` |
| Metadata Index | `metadata/binary-amd64-Packages` | 27,856 | ✅ VERIFIED | `56b7a6dcf5b849b9c02bd1c5b8a685d1b87b3c67d0c3b7acc88cceede5dbd7cb` |
| Metadata Index | `metadata/dists-resolute-Release` | 2,633 | ✅ VERIFIED | `473fb5f5ba8e221b5bdff2db2b9760426e89e928d96736979f894a04c9e74221` |
| Metadata Index | `metadata/generic-package-details.json` | 12,087 | ✅ VERIFIED | `23de71d06b4218a18465287947771c12e8d9160fd9003592b369e36a414ade5a` |
| Metadata Index | `metadata/packages-api-response.json` | 35,141 | ✅ VERIFIED | `0641f4005c9d1394722b9f8a1f6cc98fdc123e19faa2f70ca8a3165eb838a1f5` |
