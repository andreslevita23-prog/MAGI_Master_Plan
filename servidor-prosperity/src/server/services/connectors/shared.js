export function defineConnector({
  id,
  name,
  family,
  role,
  description,
  status = "mock-ready",
  inputContract,
  outputContract,
  connection,
  mock,
}) {
  return {
    id,
    name,
    family,
    role,
    description,
    status,
    inputContract,
    outputContract,
    connection,
    mock,
  };
}

export function buildConnectorSnapshot(connector) {
  return {
    id: connector.id,
    name: connector.name,
    family: connector.family,
    role: connector.role,
    description: connector.description,
    status: connector.status,
    transport: connector.connection.transport,
    target: connector.connection.target,
    mockEnabled: connector.connection.mockEnabled,
    requiredEnv: connector.connection.requiredEnv,
    inputContract: connector.inputContract,
    outputContract: connector.outputContract,
    mockSample: connector.mock.sample,
    notes: connector.mock.notes,
  };
}
