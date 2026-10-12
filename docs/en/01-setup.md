---
title: "What you need and installing Docker"
description: "Everything in this project — running it and testing it — happens inside a Docker Ubuntu 24.04 container. This chapter covers only checking the resources you nee…"
lang: en
---

# What you need and installing Docker

![An illustration of Alice and Bob, two children, playing happily](../images/alice-bob.png)

Everything in this project — running it and testing it — happens inside a Docker Ubuntu 24.04 container.
This chapter covers only checking the resources you need and installing Docker.
Building and starting the project is covered in [Setting up a working environment](03-environment.md).

> [!TIP]
> **If you already have Docker**
>
> Just check the resources in [Prerequisites](#prerequisites) and move on to [Setting up a working environment](03-environment.md).
> An explanation of Docker itself is in [Docker primer](02-docker-basics.md).

## Prerequisites

The only thing required on the host side is Docker. Python and uv are inside the container.

| Item | Amount required | Notes |
|------|-------|------|
| Docker Engine + Compose v2 | — | Docker Desktop also works |
| Memory | **6GB or more** | Measured peak 3.8GB (including the OS, while running the LLM) |
| Disk | **about 20GB** | Breakdown below |

| Contents | Size |
|------|------|
| `app` image (includes PyTorch) | 4.3GB |
| `ollama` image | 8.4GB |
| Build cache | 4.4GB |
| Volumes (embedding model + LLM + DB) | 1.9GB |

All of these are measured values on Ubuntu 24.04 (2 vCPU / 8GB).
Step 1 through Step 3 do not use the LLM, so the `ollama` image and the model
(about 9.8GB) can be put off until later.

Checking the current allocation.

{% raw %}
```bash
docker info --format 'Memory: {{.MemTotal}}'
df -h /
```
{% endraw %}

## On an underpowered machine, this is what hurts

The 20GB figure above is for **when Step 4 (the LLM) is included**.
What is heavy is not Docker, but running an LLM locally.

| What is needed | Amount | Where it hurts |
|---------|-----|--------------|
| `ollama` image | 8.4GB | The first download. On a thin connection, this is where it stalls |
| Model | 1.4GB and up | Same as above |
| `app` image | about 4GB | Because it includes PyTorch |
| Memory | 6GB or more | During inference |

On top of that, **inference inside the container runs on the CPU.**
On macOS the Apple Silicon GPU cannot be handed to a container, and even on Linux
using the GPU takes extra configuration. That is why a single question takes a dozen or more seconds.

If your machine is underpowered, it helps to scale things back as follows. **Up to Step 3, everything works with nothing scaled back.**

### 1. Read the part that does not use the LLM

Step 1 through Step 3 (ChromaDB and MCP) do not need the LLM.
Download neither the `ollama` image nor the model, and start only `app`.

```bash
docker compose up -d --no-deps app
```

Everything about how MCP works shows up by that point. **The subject of this material fits within Step 3.**

### 2. Use the Ollama on the host

If you already have Ollama installed, you can avoid downloading the 8.4GB image.
On Apple Silicon the GPU is available, so it is faster too. Write it in `.env`
([Setting up Ollama](08-ollama-setup.md)).

```bash
OLLAMA_HOST=http://host.docker.internal:11434
```

### 3. Use an even smaller model

If `qwen3:1.7b` is still too heavy, there is `qwen3:0.6b` (522MB).
However, **it fails to pick the right tool more often.** These are the results of sending three kinds of question six times each.

```
qwen3:1.7b    18/18
qwen3:0.6b    13/18
```

> [!WARNING]
> **The image download sometimes does not progress**
>
> The `ollama` image is 8.4GB, and depending on the connection it can look like
> progress has stalled while the download has in fact failed.
> If it stalls, bring things down once with `docker compose down`, then run
> `docker pull ollama/ollama` on its own and watch what happens. Once the download
> is finished, there is no need to redo it next time.

## Installing Docker

### On Ubuntu

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
```

**The result of `usermod` does not take effect until you log in again.** Log out once and log back in.
Forget it, and the next step gives you `permission denied`.

Checking the installation.

```bash
docker --version
docker compose version
docker run --rm hello-world
```

If `Hello from Docker!` appears, you are done. That it works without `sudo` can also
be confirmed at the same time here.

> [!NOTE]
> **Using Ubuntu's standard packages**
>
> It has been measured that this project works with the standard packages of
> Ubuntu 24.04 (Docker 29.1, Compose 2.40).
> There is also a way to add Docker's official repository, but the procedure gets longer.

### On macOS / Windows

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
Compose is bundled, so there is no extra work.

## Next

Once Docker works, move on to [Docker primer](02-docker-basics.md).
Vocabulary such as container, image, and volume is confirmed there with a few-line example using public images.

If you are used to Docker, you can go straight to [Setting up a working environment](03-environment.md).
