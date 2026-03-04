/**
 * AIgator Telemetry Backend
 * 
 * Google Apps Script — принимает ping от приложения, пишет в Google Sheet,
 * раз в сутки отправляет дайджест в Telegram.
 * 
 * Установка:
 * 1. Создать Google Sheet
 * 2. Extensions → Apps Script
 * 3. Вставить этот код
 * 4. Заполнить TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
 * 5. Deploy → New deployment → Web app → Anyone → Deploy
 * 6. Скопировать URL и вставить в config.py (TELEMETRY_WEBHOOK_URL)
 * 7. Настроить триггер: Triggers → Add trigger → sendDailyDigest → Time-driven → Day timer
 */

// === НАСТРОЙКИ ===
const TELEGRAM_BOT_TOKEN = "8694763342:AAG63LV5g7u2Y0OeO43l0U12RlbNCcT8sQk";
const TELEGRAM_CHAT_ID = "426590628";
const SHEET_NAME = "Telemetry";  // Имя листа в Google Sheet

/**
 * Обработка POST-запроса от приложения
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    
    const sheet = _getOrCreateSheet();
    
    // Добавляем строку: Timestamp | User ID | Version | First Launch
    sheet.appendRow([
      new Date().toISOString(),
      data.user_id || "unknown",
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
  
  // Определяем границу — последние 24 часа
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  
  // Собираем статистику за 24 часа
  const todayUsers = new Set();
  let todayLaunches = 0;
  let newInstalls = 0;
  const versions = {};
  
  // Собираем все user_id которые были ДО вчера (для определения "новых")
  const knownUsersBefore = new Set();
  
  for (let i = 1; i < data.length; i++) {
    const timestamp = new Date(data[i][0]);
    const userId = data[i][1];
    const version = data[i][2];
    const firstLaunch = data[i][3];
    
    if (timestamp < yesterday) {
      knownUsersBefore.add(userId);
      continue;
    }
    
    // Это запись за последние 24 часа
    todayUsers.add(userId);
    todayLaunches++;
    
    // Считаем версии
    versions[version] = (versions[version] || 0) + 1;
    
    // Новая установка: first_launch=YES и этот user не встречался раньше
    if (firstLaunch === "YES" && !knownUsersBefore.has(userId)) {
      newInstalls++;
    }
  }
  
  // Всего уникальных пользователей за всё время
  const allUsers = new Set();
  for (let i = 1; i < data.length; i++) {
    allUsers.add(data[i][1]);
  }
  
  // Форматируем дату
  const dateStr = _formatDate(now);
  
  // Форматируем версии
  const versionStr = Object.entries(versions)
    .sort((a, b) => b[1] - a[1])
    .map(([v, count]) => `v${v} (${count})`)
    .join(", ") || "—";
  
  // Собираем сообщение
  const message = [
    `📊 AIgator — дайджест за ${dateStr}`,
    ``,
    `• Активных за сутки: ${todayUsers.size}`,
    `• Запусков за сутки: ${todayLaunches}`,
    `• Новых установок: ${newInstalls}`,
    `• Всего пользователей: ${allUsers.size}`,
    `• Версии: ${versionStr}`,
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
 * Получить или создать лист Telemetry
 */
function _getOrCreateSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    // Заголовки
    sheet.appendRow(["Timestamp", "User ID", "Version", "First Launch"]);
    sheet.getRange(1, 1, 1, 4).setFontWeight("bold");
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
