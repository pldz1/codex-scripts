# Azure GPT-Image-2 configuration

The skill reads Azure credentials from the WSL/Linux process environment. Do not put the key in `~/.codex/auth.json`, `SKILL.md`, a Git repository, or a command-line argument.

## Recommended WSL setup

Create a private environment file:

```bash
mkdir -p ~/.config/codex
chmod 700 ~/.config/codex
cat > ~/.config/codex/azure-image.env <<'EOF_ENV'
export AZURE_OPENAI_API_KEY='replace-with-your-key'
export AZURE_OPENAI_ENDPOINT='https://YOUR-RESOURCE.openai.azure.com/'
export AZURE_OPENAI_IMAGE_DEPLOYMENT='YOUR-GPT-IMAGE-2-DEPLOYMENT-NAME'
export AZURE_OPENAI_IMAGE_API_VERSION='preview'
EOF_ENV
chmod 600 ~/.config/codex/azure-image.env
```

Load it from your shell profile:

```bash
printf '%s\n' 'source ~/.config/codex/azure-image.env' >> ~/.bashrc
source ~/.bashrc
```

`AZURE_OPENAI_ENDPOINT` may be either the Azure resource endpoint, such as:

```text
https://YOUR-RESOURCE.openai.azure.com/
```

or an Azure v1 base URL, such as:

```text
https://YOUR-RESOURCE.openai.azure.com/openai/v1/
```

The script normalizes both forms to the image generations endpoint.

The deployment variable is the deployment name you assigned in Azure, which is not necessarily identical to the underlying model name.

## Verify configuration

From the installed skill directory:

```bash
python3 scripts/azure_image_generate.py --check
```

The command reports whether the key is set but never prints the key.

## Test generation

```bash
python3 scripts/azure_image_generate.py \
  --size 1024x1024 \
  --quality high \
  --output-dir ~/generated-images <<'PROMPT'
A minimal isometric illustration of a Linux development workstation running WSL2 and Docker Engine, white background, crisp technical diagram, no logos, no watermark.
PROMPT
```

## Custom base URL

For a gateway or proxy that already exposes the complete generations URL, set `AZURE_OPENAI_BASE_URL` to a URL ending in `/images/generations`. When both endpoint variables exist, `AZURE_OPENAI_ENDPOINT` takes precedence.

## Troubleshooting

- HTTP 401: verify the API key belongs to the Azure resource represented by the endpoint.
- HTTP 404 or `DeploymentNotFound`: verify the deployment name, resource endpoint, and regional model availability.
- HTTP 429: the deployment quota is exhausted or rate-limited; reduce `--n` or retry later.
- TLS or connection errors: verify WSL proxy, corporate certificates, DNS, VPN, and Azure private endpoint access.
