process.env.NODE_ENV = "test";

const { buildServer } = await import("../src/server/index.js");

const app = buildServer();
await app.ready();

const response = await app.inject({
  method: "POST",
  url: "/api/users/00000000-0000-0000-0000-000000000000/approve",
  payload: {
    dualControlRequestId: "11111111-1111-1111-1111-111111111111",
    approverId: "22222222-2222-2222-2222-222222222222",
    secondaryApproverId: "33333333-3333-3333-3333-333333333333",
    // intentionally missing `reason`
  },
});

console.log(
  JSON.stringify(
    {
      statusCode: response.statusCode,
      body: response.body,
    },
    null,
    2,
  ),
);

await app.close();
