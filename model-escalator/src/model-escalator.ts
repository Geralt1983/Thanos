import * as winston from 'winston';
import { 
  ModelConfig, 
  ModelRequest, 
  ModelEscalatorConfig, 
  EscalationStrategy 
} from './types';
import { DefaultComplexityScorer } from './complexity-scorer';

export class ModelEscalator {
  private config: ModelEscalatorConfig;
  private complexityScorer: DefaultComplexityScorer;
  private logger: winston.Logger;

  constructor(config: ModelEscalatorConfig) {
    this.config = config;
    this.complexityScorer = new DefaultComplexityScorer();
    this.logger = this.setupLogger();
  }

  private setupLogger(): winston.Logger {
    return winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'model-escalator.log' })
      ]
    });
  }

  public async processRequest(request: ModelRequest): Promise<{ 
    result: string, 
    modelUsed: string, 
    complexity: number 
  }> {
    try {
      const complexity = this.complexityScorer.calculateComplexity(request.input);
      this.logger.info(`Request complexity detected: ${complexity}`);

      const selectedModel = this.selectModel(complexity);
      
      // Simulate model processing (replace with actual model call)
      const result = await this.mockModelCall(selectedModel, request);

      return {
        result,
        modelUsed: selectedModel.name,
        complexity
      };
    } catch (error) {
      this.logger.error('Model escalation failed', { error, request });
      throw error;
    }
  }

  private selectModel(complexity: number): ModelConfig {
    // Sort models by increasing complexity capability
    const sortedModels = this.config.models.sort((a, b) => 
      a.complexity.maxComplexity - b.complexity.maxComplexity
    );

    switch (this.config.defaultStrategy) {
      case EscalationStrategy.LINEAR:
        return this.linearModelSelection(sortedModels, complexity);
      case EscalationStrategy.EXPONENTIAL:
        return this.exponentialModelSelection(sortedModels, complexity);
      case EscalationStrategy.ADAPTIVE:
      default:
        return this.adaptiveModelSelection(sortedModels, complexity);
    }
  }

  private linearModelSelection(models: ModelConfig[], complexity: number): ModelConfig {
    // Simple linear model selection based on complexity thresholds
    return models.find(model => 
      complexity <= model.complexity.maxComplexity
    ) || models[models.length - 1];
  }

  private exponentialModelSelection(models: ModelConfig[], complexity: number): ModelConfig {
    // More aggressive model escalation
    return models.find(model => 
      complexity <= model.complexity.maxComplexity * 1.5
    ) || models[models.length - 1];
  }

  private adaptiveModelSelection(models: ModelConfig[], complexity: number): ModelConfig {
    // Most sophisticated selection considering multiple factors
    const contextualModels = models.filter(model => 
      complexity <= model.complexity.maxComplexity
    );

    if (contextualModels.length === 0) {
      return models[models.length - 1]; // Fallback to most powerful model
    }

    // Select model with closest matching complexity
    return contextualModels.reduce((prev, curr) => 
      Math.abs(curr.complexity.maxComplexity - complexity) < 
      Math.abs(prev.complexity.maxComplexity - complexity) 
        ? curr 
        : prev
    );
  }

  private async mockModelCall(model: ModelConfig, request: ModelRequest): Promise<string> {
    // Simulate model call - replace with actual model invocation
    this.logger.info(`Processing request with model: ${model.name}`);
    return `Processed by ${model.name} with complexity ${request.input.length}`;
  }
}