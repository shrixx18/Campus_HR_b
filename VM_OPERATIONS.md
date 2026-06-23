# Backend VM Operations Manual

Use this when you want to stop the Azure VM to save student subscription credits, then start it again later.

## Current Backend

```text
VM name: CmpVM
Resource group: Campus_HR_b
Public backend URL: http://20.219.9.65:8080
Project folder on VM: ~/Campus_HR_b
```

## Important Cost Note

To save VM compute cost, the VM must be **Stopped (deallocated)**.

If you only shut down Linux from inside the VM with `sudo shutdown now`, Azure may show the VM as **Stopped** but not **Deallocated**, and some compute cost can continue. Prefer stopping it from Azure Portal or Azure CLI.

## Stop Backend and VM

### Option 1: Azure Portal

1. Go to Azure Portal.
2. Open Virtual Machines.
3. Select `CmpVM`.
4. Click **Stop**.
5. Confirm the stop action.
6. Wait until the VM status is:

```text
Stopped (deallocated)
```

This is the easiest and safest method.

### Option 2: Azure CLI

Run this from your laptop terminal or Azure Cloud Shell:

```bash
az vm deallocate --resource-group Campus_HR_b --name CmpVM
```

Check status:

```bash
az vm get-instance-view \
  --resource-group Campus_HR_b \
  --name CmpVM \
  --query "instanceView.statuses[].displayStatus" \
  --output table
```

You want to see:

```text
VM deallocated
```

## Start VM and Backend

### Option 1: Azure Portal

1. Go to Azure Portal.
2. Open Virtual Machines.
3. Select `CmpVM`.
4. Click **Start**.
5. Wait until status is:

```text
Running
```

### Option 2: Azure CLI

```bash
az vm start --resource-group Campus_HR_b --name CmpVM
```

Check status:

```bash
az vm get-instance-view \
  --resource-group Campus_HR_b \
  --name CmpVM \
  --query "instanceView.statuses[].displayStatus" \
  --output table
```

You want to see:

```text
VM running
```

## Start Containers After VM Starts

SSH into the VM:

```powershell
ssh -i "C:\Users\91982\Downloads\CmpVM_key.pem" azureuser@20.219.9.65
```

Then run:

```bash
cd ~/Campus_HR_b
docker compose up -d
docker compose ps
```

All containers should become `running` or `healthy`.

Test from the VM:

```bash
curl http://localhost:8080/health
```

Test from your browser:

```text
http://20.219.9.65:8080/health
```

If Docker restart policies are configured, the containers may come up automatically after the VM starts. If the health URL does not respond, SSH in and run:

```bash
cd ~/Campus_HR_b
docker compose up -d
```

## Stop Only Backend Containers

If you want to stop the backend but keep the VM running:

```bash
cd ~/Campus_HR_b
docker compose down
```

This stops containers but does **not** save VM compute cost. Use VM deallocation to save cost.

## Restart Backend Containers

Use this after editing `.env`, `docker-compose.yml`, or Nginx config:

```bash
cd ~/Campus_HR_b
docker compose down
docker compose up -d
docker compose ps
```

## Logs and Troubleshooting

Check all containers:

```bash
docker compose ps
```

Check gateway:

```bash
docker compose logs --tail=100 api-gateway
```

Check a service:

```bash
docker compose logs --tail=150 identity-service
docker compose logs --tail=150 opportunity-service
docker compose logs --tail=150 application-service
docker compose logs --tail=150 communications-service
```

Check VM memory:

```bash
free -h
```

Check Docker resource usage:

```bash
docker stats --no-stream
```

## Public IP Warning

If the VM uses a dynamic public IP, the IP address may change after stopping/deallocating the VM.

After starting the VM, confirm the public IP in Azure Portal. If it changes, update:

1. Frontend Vercel rewrite destination.
2. Any frontend/backend documentation using the old IP.
3. Browser test URL.

To avoid this, assign a static public IP in Azure.

## CI/CD Note

By default, Azure will not automatically pull the latest GitHub changes when the VM starts. A plain VM only restarts whatever code is already on disk.

This repo includes a GitHub Actions workflow at `.github/workflows/deploy-backend.yml` and a VM deploy script at `scripts/deploy.sh`.

To use it, add these GitHub Actions secrets in the backend repository:

| Secret | Example |
| --- | --- |
| `AZURE_VM_HOST` | `20.219.9.65` |
| `AZURE_VM_USER` | `azureuser` |
| `AZURE_VM_SSH_KEY` | Contents of `CmpVM_key.pem` |
| `AZURE_VM_DEPLOY_PATH` | `/home/azureuser/Campus_HR_b` |
| `AZURE_VM_DEPLOY_BRANCH` | `main` |

After those secrets are configured, every push to `main` will:

1. SSH into the VM.
2. Pull the latest backend code.
3. Rebuild and restart the Docker Compose stack.
4. Check the local health endpoint.
