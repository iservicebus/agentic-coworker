import apiClient from './apiClient';

enum LogLevel {
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

function log(level: LogLevel, message: string, ...optionalParams: any[]) {
  const logMessage = `[${level}] ${message} ${optionalParams.map(p => JSON.stringify(p)).join(' ')}`.trim();

  // Log to server
  apiClient('/logs/', {
    method: 'POST',
    body: JSON.stringify({ message: logMessage }),
    includeAuth: false,
  }).catch(console.error);

  // Also log to browser console
  switch (level) {
    case LogLevel.INFO:
      console.log(logMessage);
      break;
    case LogLevel.WARN:
      console.warn(logMessage);
      break;
    case LogLevel.ERROR:
      console.error(logMessage);
      break;
  }
}

export const logger = {
  info: (message: string, ...optionalParams: any[]) => log(LogLevel.INFO, message, ...optionalParams),
  warn: (message: string, ...optionalParams: any[]) => log(LogLevel.WARN, message, ...optionalParams),
  error: (message: string, ...optionalParams: any[]) => log(LogLevel.ERROR, message, ...optionalParams),
};
