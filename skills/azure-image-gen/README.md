# Azure GPT-Image-2 Codex skill

A local Codex skill that generates image files through an Azure OpenAI GPT-Image-2 deployment.

## Install

```bash
tar -xzf azure-image-gen-skill.tar.gz
cd azure-image-gen
./install.sh
```

The installer copies the skill to:

```text
~/.agents/skills/azure-image-gen
```

## Configure

Set these variables in WSL:

```bash
export AZURE_OPENAI_API_KEY='...'
export AZURE_OPENAI_ENDPOINT='https://YOUR-RESOURCE.openai.azure.com/'
export AZURE_OPENAI_IMAGE_DEPLOYMENT='YOUR-DEPLOYMENT-NAME'
```

See `references/configuration.md` for a persistent and permission-restricted setup.

## Use in Codex

Explicit invocation:

```text
$azure-image-gen Generate a 1536x1024 cinematic concept image of ...
```

You can also ask normally; the skill permits implicit invocation for image-generation requests.

## Direct test

```bash
python3 ~/.agents/skills/azure-image-gen/scripts/azure_image_generate.py --check
```
