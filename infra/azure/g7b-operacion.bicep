// Mantenimiento del Job existente. Dependencias conservadas, no recreadas.
// Usar consolidar_azure.sh --plan; no desplegar sin revisar el what-if.
targetScope = 'resourceGroup'

@description('Etiquetas recuperadas del Job actual; no sustituirlas por un conjunto inventado.')
param jobTags object

@description('Perfil actual recuperado de Azure; vacio conserva la asignacion implicita.')
param workloadProfileName string = ''

var region = 'westus2'
var digest = 'g7bacr09b52a0e.azurecr.io/g7b/auditoria@sha256:aa21dd18f24ed19e24b7d32e2fe6ea514e97e873fbc677c15b22996ddec8319d'

resource environment 'Microsoft.App/managedEnvironments@2026-07-01' existing = {
  name: 'g7b-env-laboratorio-jobs-v3'
}
resource acr 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: 'g7bacr09b52a0e'
}
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: 'g7b-logs-laboratorio'
}
resource publisher 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: 'g7b-github-acr'
}
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: 'g7blago09b52a0e'
}

resource job 'Microsoft.App/jobs@2024-03-01' = {
  name: 'g7b-smoke-laboratorio'
  location: region
  tags: jobTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: union({
    environmentId: environment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: 'g7bacr09b52a0e.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'smoke'
          image: digest
          command: ['python']
          args: ['/opt/g7b/g7b_ops/auditoria.py']
          env: [
            {
              name: 'AZURE_STORAGE_ACCOUNT_URL'
              value: 'https://g7blago09b52a0e.blob.core.windows.net'
            }
            {
              name: 'AZURE_CONTAINER_NAME'
              value: 'lago'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }, empty(workloadProfileName) ? {} : { workloadProfileName: workloadProfileName })
}

// Referencias verificadas por el preflight; no conceder nuevos roles con nuevos GUID.
output dependencias object = {
  environment: environment.id
  acr: acr.id
  workspace: workspace.id
  publisher: publisher.id
  storage: storage.id
}
