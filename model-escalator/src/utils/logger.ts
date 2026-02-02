import winston from 'winston';

export class Logger {
  private logger: winston.Logger;

  constructor(context: string) {
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.printf(({ timestamp, level, message, context: ctx }) => {
          return `${timestamp} [${ctx}] ${level}: ${message}`;
        })
      ),
      defaultMeta: { context },
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ 
          filename: 'logs/model-escalator.log',
          maxsize: 5 * 1024 * 1024, // 5MB
          maxFiles: 5
        })
      ]
    });
  }

  info(message: string) {
    this.logger.info(message);
  }

  error(message: string, error?: Error) {
    this.logger.error(message, error);
  }

  warn(message: string) {
    this.logger.warn(message);
  }

  debug(message: string) {
    this.logger.debug(message);
  }
}