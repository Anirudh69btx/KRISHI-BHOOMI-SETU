import Fastify from "fastify";
import cors from "@fastify/cors";
import { connect, JSONCodec } from "nats";
import Redis from "ioredis";

const fastify = Fastify({ logger: true });

const NATS_URL = process.env.NATS_URL || "nats://localhost:4222";
const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379/2";
const PORT = parseInt(process.env.PORT || "3001", 10);

const jc = JSONCodec();

async function start() {
  await fastify.register(cors, {
    origin: true,
  });

  const redis = new Redis(REDIS_URL, { lazyConnect: true });
  try {
    await redis.connect();
    fastify.log.info("Connected to Redis");
  } catch (err) {
    fastify.log.warn({ err }, "Redis connection failed, running degraded");
  }

  let nc;
  try {
    nc = await connect({ servers: NATS_URL });
    fastify.log.info(`Connected to NATS at ${NATS_URL}`);

    // Subscribe to regional outbreak detections
    const sub = nc.subscribe("region.*.outbreak.detected");
    (async () => {
      for await (const msg of sub) {
        try {
          const alert = jc.decode(msg.data) as Record<string, unknown>;
          fastify.log.info({ subject: msg.subject, alert }, "Received regional outbreak detected event");
          // Cache alert in redis for rapid lookups
          if (redis.status === "ready") {
            const alertId = (alert.id as string) || "latest";
            await redis.setex(`alert:${alertId}`, 86400, JSON.stringify(alert));
          }
        } catch (decErr) {
          fastify.log.error({ decErr }, "Failed to decode NATS alert message");
        }
      }
    })();
  } catch (err) {
    fastify.log.warn({ err }, "NATS connection failed, retry scheduled");
  }

  // Health route
  fastify.get("/health", async () => {
    return {
      status: "ok",
      service: "flip-alert-engine",
      natsConnected: nc ? !nc.isClosed() : false,
      redisConnected: redis.status === "ready",
    };
  });

  // Active alerts
  fastify.get("/api/v1/alerts/active", async (req, reply) => {
    return {
      alerts: [],
    };
  });

  // Manual broadcast endpoint
  fastify.post("/api/v1/alerts/broadcast", async (req, reply) => {
    const payload = req.body;
    if (nc && !nc.isClosed()) {
      nc.publish("disaster.broadcast", jc.encode(payload));
      return { status: "queued", payload };
    }
    reply.status(503);
    return { error: "NATS broker unavailable" };
  });

  try {
    await fastify.listen({ port: PORT, host: "0.0.0.0" });
    fastify.log.info(`Alert Engine listening on port ${PORT}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
}

start();
