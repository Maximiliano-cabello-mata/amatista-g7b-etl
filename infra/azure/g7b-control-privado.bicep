// G7B: base de cómputo bajo demanda en Azure, sin datos ni secretos en la plantilla.
// Aún NO es el worker de DuckDB: es el recurso de ejecución aislada y su identidad.
// No crea almacenamiento nuevo: usa la cuenta y el contenedor 'lago' existentes.
// Los despliegues se inician a mano tras remediar la SAS expuesta.
targetScope = 'resourceGroup'

@description('Cuenta Blob Storage G7B existente dentro de este grupo.')
@minLength(3)
param storageAccountName string

@allowed(['laboratorio', 'validacion'])
param stage string = 'laboratorio'

param containerName string = 'lago'
param location string = resourceGroup().location

@description('Desactivado hasta rotar las credenciales y revisar la facturación.')
param provisionCompute bool = false

@description('Imagen OCI: por defecto smoke oficial. Para diagnóstico real, usar imagen G7B construida en ACR.')
param workerImage string = 'mcr.microsoft.com/k8se/quickstart-jobs:latest'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  parent: storage
  name: 'default'
}
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = {
  parent: blobService
  name: containerName
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = if (provisionCompute) {
  name: 'g7b-env-${stage}'
  location: location
  tags: {
    proyecto: 'g7b'
    fase: stage
    datos: 'privados'
  }
  properties: {
    appLogsConfiguration: {
      destination: 'none'
    }
  }
}

resource job 'Microsoft.App/jobs@2024-03-01' = if (provisionCompute) {
  name: 'g7b-smoke-${stage}'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  tags: {
    proyecto: 'g7b'
    fase: stage
    uso: 'smoke-test'
  }
  properties: {
    environmentId: environment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'smoke'
          image: workerImage
          env: [
            {
              name: 'AZURE_STORAGE_ACCOUNT_URL'
              value: 'https://${storageAccountName}.blob.core.windows.net'
            }
            {
              name: 'AZURE_CONTAINER_NAME'
              value: containerName
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

// Minimo privilegio en el contenedor; lector, nunca escritor ni borrador.
// El despliegue requiere el permiso de crear asignaciones RBAC.
var blobDataReader = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
resource jobReadAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (provisionCompute) {
  name: guid(blobContainer.id, job.id, blobDataReader)
  scope: blobContainer
  properties: {
    principalId: job!.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: blobDataReader
  }
}

output storageId string = storage.id
output scopeDeLectura string = blobContainer.id
output nombreJob string = provisionCompute ? job.name : 'no-desplegado'
output aprovisionaCompute bool = provisionCompute
