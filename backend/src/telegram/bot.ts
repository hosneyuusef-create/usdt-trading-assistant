import { Bot } from "grammy";
import { env } from "../config/env.js";
import { logger } from "../utils/logger.js";
import { listPendingDualControlRequests } from "../domain/dual-control.js";

let botInstance: Bot | null = null;

export const startTelegramBot = () => {
  if (!env.TELEGRAM_BOT_TOKEN) {
    logger.warn("Telegram bot token not configured; skipping bot startup");
    return null;
  }

  if (botInstance) {
    return botInstance;
  }

  botInstance = new Bot(env.TELEGRAM_BOT_TOKEN);
  botInstance.catch((error) => {
    logger.error({ err: error }, "Telegram bot error");
  });

  botInstance.command("health", async (ctx) => {
    await ctx.reply(
      `USDT Trading Assistant is healthy at ${new Date().toISOString()}`,
    );
  });

  botInstance.command("dualcontrol", async (ctx) => {
    const pending = await listPendingDualControlRequests();
    if (!pending.length) {
      await ctx.reply("No pending approvals ✅");
      return;
    }
    const formatted = pending
      .map((item) => {
        const reason = item.approvalReason
          ? ` reason: ${item.approvalReason}`
          : "";
        return `• ${item.entityType} (${item.action}) for ${item.entityId} requested by ${item.requestedBy}${reason}`;
      })
      .join("\n");
    await ctx.reply(`Pending approvals:\n${formatted}`);
  });

  botInstance.start();
  logger.info("Telegram bot started");
  return botInstance;
};

export const stopTelegramBot = async () => {
  if (botInstance) {
    await botInstance.stop();
    botInstance = null;
  }
};
