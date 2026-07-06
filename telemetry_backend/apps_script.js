/**
 * AIgator Telemetry Backend
 *
 * Google Apps Script — принимает анонимный ping от приложения (только версия
 * и флаг первого запуска, БЕЗ идентификаторов), пишет в Google Sheet,
 * раз в сутки отправляет дайджест в Telegram.
 *
 * Приложение пингует не чаще раза в сутки, поэтому:
 *   пингов за день = активных установок за день (DAU).
 *
 * Установка:
 * 1. Создать Google Sheet
 * 2. Extensions → Apps Script
 * 3. Вставить этот код
 * 4. Заполнить TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID (НЕ коммитить настоящие!)
 * 5. Deploy → New deployment → Web app → Anyone → Deploy
 * 6. Скопировать URL и вставить в config.py (TELEMETRY_WEBHOOK_URL)
 * 7. Настроить триггер: Triggers → Add trigger → sendDailyDigest → Time-driven → Day timer
 */

// === НАСТРОЙКИ ===
const TELEGRAM_BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN"; // токен от @BotFather — настоящий токен в репозиторий не коммитить!
const TELEGRAM_CHAT_ID = "PASTE_YOUR_CHAT_ID";     // ваш chat id — можно узнать у @userinfobot
const SHEET_NAME = "Telemetry_v2";  // v2: без колонки User ID (анонимно с v1.2.0)

/**
 * Обработка POST-запроса от приложения
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    const sheet = _getOrCreateSheet();

    // Добавляем строку: Timestamp | Version | First Launch
    sheet.appendRow([
      new Date().toISOString(),
      data.version || "unknown",
      data.first_launch ? "YES" : "NO"
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Отправка ежедневного дайджеста в Telegram.
 * Настроить как триггер: Triggers → Add trigger → Day timer
 */
function sendDailyDigest() {
  const sheet = _getOrCreateSheet();
  const data = sheet.getDataRange().getValues();

  if (data.length <= 1) {
    // Только заголовок, данных нет
    _sendTelegram("📊 AIgator — нет данных за сегодня");
    return;
  }

  // Граница — последние 24 часа
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);

  let dau = 0;            // пингов за 24ч = активных установок за день
  let newInstalls = 0;    // first_launch=YES за 24ч
  let totalInstalls = 0;  // first_launch=YES за всё время
  const versions = {};

  for (let i = 1; i < data.length; i++) {
    const timestamp = new Date(data[i][0]);
    const version = data[i][1];
    const firstLaunch = data[i][2];

    if (firstLaunch === "YES") {
      totalInstalls++;
    }

    if (timestamp < yesterday) {
      continue;
    }

    // Запись за последние 24 часа
    dau++;
    versions[version] = (versions[version] || 0) + 1;
    if (firstLaunch === "YES") {
      newInstalls++;
    }
  }

  const dateStr = _formatDate(now);

  const versionStr = Object.entries(versions)
    .sort((a, b) => b[1] - a[1])
    .map(([v, count]) => `v${v} (${count})`)
    .join(", ") || "—";

  const message = [
    `📊 AIgator — дайджест за ${dateStr}`,
    ``,
    `• Активных за сутки (DAU): ${dau}`,
    `• Новых установок за сутки: ${newInstalls}`,
    `• Установок за всё время: ${totalInstalls}`,
    `• Версии за сутки: ${versionStr}`,
  ].join("\n");

  _sendTelegram(message);
}

/**
 * Отправить сообщение в Telegram
 */
function _sendTelegram(text) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({
      chat_id: TELEGRAM_CHAT_ID,
      text: text,
      parse_mode: "HTML"
    })
  };

  UrlFetchApp.fetch(url, options);
}

/**
 * Получить или создать лист Telemetry_v2
 */
function _getOrCreateSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);

  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    // Заголовки
    sheet.appendRow(["Timestamp", "Version", "First Launch"]);
    sheet.getRange(1, 1, 1, 3).setFontWeight("bold");
  }

  return sheet;
}

/**
 * Форматировать дату в DD.MM.YYYY
 */
function _formatDate(date) {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}.${month}.${year}`;
}

/**
 * Тест — вручную отправить дайджест (для проверки)
 */
function testDigest() {
  sendDailyDigest();
}
