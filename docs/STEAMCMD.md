# Bundled SteamCMD

The repository includes Valve's signed `steamcmd.exe` so the packaged application
can bootstrap SteamCMD without a separate user installation.

Current bundled binary:

- File version: `10.77.20.88`
- Product version: `01.00.00.02`
- Size: `5,460,120` bytes
- SHA-256: `61BD59C413EDCB2EF6D0EBB6E7F255D29EAAA5507C6C01D3D03F747D335D6603`
- Authenticode signer: `Valve Corp.`
- Signature status when committed: `Valid`

When updating the binary, verify its Authenticode signature and update every value
above in the same commit.
