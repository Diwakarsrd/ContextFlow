import { startServer, stopServer } from "./setup.js";

export async function setup(): Promise<void> {
  await startServer();
}

export async function teardown(): Promise<void> {
  stopServer();
}
