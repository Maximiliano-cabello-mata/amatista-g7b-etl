// Ruta candidata para Azure Monitor. NO cambia el destino del entorno.
// Aplicar coordinadamente con el cambio de destino, tras revisar el plan.
targetScope = 'resourceGroup'

resource environment 'Microsoft.App/managedEnvironments@2026-07-01' existing = {
  name: 'g7b-env-laboratorio-jobs-v3'
}
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: 'g7b-logs-laboratorio'
}
resource logs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'g7b-console-system'
  scope: environment
  properties: {
    workspaceId: workspace.id
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      {
        category: 'ContainerAppConsoleLogs'
        enabled: true
      }
      {
        category: 'ContainerAppSystemLogs'
        enabled: true
      }
    ]
  }
}
