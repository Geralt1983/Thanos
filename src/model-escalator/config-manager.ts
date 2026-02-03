import fs from 'fs';
import path from 'path';
import { ModelEscalatorConfig } from './types';
import { Logger } from '../core/logger';

export class ModelEscalatorConfigManager {
  private static CONFIG_PATH = path.join(process.cwd(), 'config', 'model-escalator.json');
  private logger: Logger;

  constructor(logger: Logger) {
    this.logger = logger;
  }

  loadConfig(): ModelEscalatorConfig {
    try {
      if (!fs.existsSync(ModelEscalatorConfigManager.CONFIG_PATH)) {
        return this.createDefaultConfig();
      }

      const rawConfig = fs.readFileSync(ModelEscalatorConfigManager.CONFIG_PATH, 'utf-8');
      const config: ModelEscalatorConfig = JSON.parse(rawConfig);
      
      this.validateConfig(config);
      return config;
    } catch (error) {
      this.logger.error('ModelEscalatorConfigManager', {
        event: 'CONFIG_LOAD_ERROR',
        error: error instanceof Error ? error.message : String(error)
      });
      
      return this.createDefaultConfig();
    }
  }

  saveConfig(config: ModelEscalatorConfig): void {
    try {
      this.validateConfig(config);
      
      const configDir = path.dirname(ModelEscalatorConfigManager.CONFIG_PATH);
      if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true });
      }

      fs.writeFileSync(
        ModelEscalatorConfigManager.CONFIG_PATH, 
        JSON.stringify(config, null, 2)
      );

      this.logger.info('ModelEscalatorConfigManager', {
        event: 'CONFIG_SAVED',
        path: ModelEscalatorConfigManager.CONFIG_PATH
      });
    } catch (error) {
      this.logger.error('ModelEscalatorConfigManager', {
        event: 'CONFIG_SAVE_ERROR',
        error: error instanceof Error ? error.message : String(error)
      });
    }
  }

  private createDefaultConfig(): ModelEscalatorConfig {
    return {
      defaultModel: 'anthropic/claude-3-5-haiku-20241022',
      plugins: [],
      complexityThresholds: {
        low: 3,
        medium: 7,
        high: 9
      },
      performanceThresholds: {
        maxLatency: 500,
        maxTokenConsumption: 100000
      }
    };
  }

  private validateConfig(config: ModelEscalatorConfig): void {
    if (!config.defaultModel) {
      throw new Error('Default model must be specified');
    }

    if (config.complexityThresholds.low >= config.complexityThresholds.medium) {
      throw new Error('Low complexity threshold must be less than medium threshold');
    }

    if (config.complexityThresholds.medium >= config.complexityThresholds.high) {
      throw new Error('Medium complexity threshold must be less than high threshold');
    }

    if (config.performanceThresholds.maxLatency <= 0) {
      throw new Error('Max latency must be a positive number');
    }

    if (config.performanceThresholds.maxTokenConsumption <= 0) {
      throw new Error('Max token consumption must be a positive number');
    }
  }

  watchConfigFile(onChange: (config: ModelEscalatorConfig) => void): fs.FSWatcher {
    return fs.watch(ModelEscalatorConfigManager.CONFIG_PATH, (eventType) => {
      if (eventType === 'change') {
        try {
          const updatedConfig = this.loadConfig();
          onChange(updatedConfig);
        } catch (error) {
          this.logger.error('ModelEscalatorConfigManager', {
            event: 'CONFIG_WATCH_ERROR',
            error: error instanceof Error ? error.message : String(error)
          });
        }
      }
    });
  }
}