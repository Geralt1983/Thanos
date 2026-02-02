import { ModelEscalatorConfig, ModelComplexityLevel } from './types';
import { ComplexityAnalyzer } from './complexity-analyzer';
import { Logger } from '../core/logger';
import { ModelRegistry } from '../core/model-registry';

export class ModelEscalator {
  private config: ModelEscalatorConfig;
  private logger: Logger;
  private modelRegistry: ModelRegistry;

  constructor(
    config: ModelEscalatorConfig, 
    logger: Logger, 
    modelRegistry: ModelRegistry
  ) {
    this.config = config;
    this.logger = logger;
    this.modelRegistry = modelRegistry;
  }

  async processInput(input: string, currentModel: string): Promise<string> {
    const start = Date.now();
    
    try {
      // Analyze complexity
      const complexityScore = await ComplexityAnalyzer.analyzeComplexity(input);
      const complexityLevel = ComplexityAnalyzer.determineComplexityLevel(complexityScore.score);

      // Determine appropriate model
      const selectedModel = await this.selectModelForComplexity(complexityLevel, currentModel);

      // Log model switch if changed
      if (selectedModel !== currentModel) {
        this.logger.info('ModelEscalator', {
          event: 'MODEL_SWITCH',
          fromModel: currentModel,
          toModel: selectedModel,
          complexityLevel
        });
      }

      // Performance tracking
      const processingTime = Date.now() - start;
      if (processingTime > this.config.performanceThresholds.maxLatency) {
        this.logger.warn('ModelEscalator', {
          event: 'PERFORMANCE_THRESHOLD_EXCEEDED',
          processingTime,
          maxLatency: this.config.performanceThresholds.maxLatency
        });
      }

      // Use selected model for processing
      return await this.modelRegistry.process(selectedModel, input);

    } catch (error) {
      this.logger.error('ModelEscalator', {
        event: 'PROCESSING_ERROR',
        input: input.slice(0, 100) + '...',
        error: error instanceof Error ? error.message : String(error)
      });
      
      // Fallback to default model
      return await this.modelRegistry.process(this.config.defaultModel, input);
    }
  }

  private async selectModelForComplexity(
    complexityLevel: ModelComplexityLevel, 
    currentModel: string
  ): Promise<string> {
    // Plugin-based model selection
    for (const plugin of this.config.plugins) {
      const recommendation = await plugin.selectAppropriateModel({
        score: complexityLevel === ModelComplexityLevel.LOW ? 1 : 
               complexityLevel === ModelComplexityLevel.MEDIUM ? 5 : 9,
        factors: {
          tokenCount: 0,
          contextDepth: 0,
          semanticComplexity: 0,
          languageSpecificity: 0
        }
      });

      if (recommendation) {
        return recommendation.name;
      }
    }

    // Default fallback logic
    switch (complexityLevel) {
      case ModelComplexityLevel.LOW:
        return this.config.defaultModel;
      case ModelComplexityLevel.MEDIUM:
        return this.modelRegistry.getNextTierModel(currentModel);
      case ModelComplexityLevel.HIGH:
        return this.modelRegistry.getHighestCapacityModel();
      default:
        return this.config.defaultModel;
    }
  }

  // Configuration update methods
  updateConfig(newConfig: Partial<ModelEscalatorConfig>) {
    this.config = { ...this.config, ...newConfig };
    this.logger.info('ModelEscalator', {
      event: 'CONFIG_UPDATED',
      changes: Object.keys(newConfig)
    });
  }
}