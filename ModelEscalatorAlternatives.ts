// Alternative ModelEscalator Configurations and API Designs

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Original Enum for Model Tiers
enum ModelTier {
  HAIKU = 'anthropic/claude-3-5-haiku-20241022',
  SONNET = 'anthropic/claude-sonnet-4-0',
  OPUS = 'anthropic/claude-opus-4-5'
}

// Alternative 1: More Granular Complexity Detection
class DetailedModelEscalator {
  private complexityRules = {
    tokenBrackets: [
      { max: 100, model: ModelTier.HAIKU, description: 'Very short tasks' },
      { max: 500, model: ModelTier.HAIKU, description: 'Simple tasks' },
      { max: 1000, model: ModelTier.SONNET, description: 'Moderate complexity' },
      { max: Infinity, model: ModelTier.OPUS, description: 'Complex tasks' }
    ],
    keywordWeights: {
      'algorithm': 3,
      'machine learning': 5,
      'architecture': 4,
      'optimization': 3,
      'system design': 4,
      'deep learning': 5,
      'refactor': 2
    }
  };

  async detectAndEscalate(context: string): Promise<ModelTier> {
    const tokenCount = this.countTokens(context);
    const keywordScore = this.calculateKeywordScore(context);
    
    const bracket = this.complexityRules.tokenBrackets
      .find(b => tokenCount <= b.max);
    
    return bracket.model;
  }

  private calculateKeywordScore(context: string): number {
    return Object.entries(this.complexityRules.keywordWeights)
      .reduce((score, [keyword, weight]) => 
        score + (context.includes(keyword) ? weight : 0), 0);
  }

  private countTokens(text: string): number {
    return text.split(/\s+/).length;
  }
}

// Alternative 2: Functional API with Per-Task Override
class FunctionalModelEscalator {
  private defaultConfig = {
    baseThreshold: 500,
    signals: [
      { pattern: /algorithm/i, weight: 2 },
      { pattern: /machine learning/i, weight: 3 },
      { pattern: /system design/i, weight: 2 }
    ]
  };

  async escalateModel(
    context: string, 
    customConfig?: Partial<typeof this.defaultConfig>
  ): Promise<ModelTier> {
    const config = { ...this.defaultConfig, ...customConfig };
    const tokenCount = this.countTokens(context);
    const signalScore = this.calculateSignalScore(context, config.signals);

    if (tokenCount > config.baseThreshold + signalScore) {
      return ModelTier.OPUS;
    } else if (tokenCount > config.baseThreshold / 2 + signalScore) {
      return ModelTier.SONNET;
    }

    return ModelTier.HAIKU;
  }

  private countTokens(text: string): number {
    return text.split(/\s+/).length;
  }

  private calculateSignalScore(
    context: string, 
    signals: Array<{pattern: RegExp, weight: number}>
  ): number {
    return signals.reduce((score, signal) => 
      score + (signal.pattern.test(context) ? signal.weight : 0), 0);
  }
}

// Alternative 3: Event-Driven Model Escalation
class EventModelEscalator {
  private currentModel: ModelTier = ModelTier.HAIKU;
  private listeners: Array<(context: string) => Promise<ModelTier | null>> = [];

  constructor() {
    // Default complexity listener
    this.addEscalationListener(this.defaultComplexityDetector);
  }

  async addEscalationListener(
    listener: (context: string) => Promise<ModelTier | null>
  ) {
    this.listeners.push(listener);
  }

  async processTask(context: string): Promise<void> {
    for (const listener of this.listeners) {
      const suggestedModel = await listener(context);
      if (suggestedModel) {
        await this.switchModel(suggestedModel);
        break;
      }
    }
  }

  private async defaultComplexityDetector(context: string): Promise<ModelTier | null> {
    const tokenCount = context.split(/\s+/).length;
    if (tokenCount > 1000) return ModelTier.OPUS;
    if (tokenCount > 500) return ModelTier.SONNET;
    return null;
  }

  private async switchModel(model: ModelTier): Promise<void> {
    await execAsync(`openclaw session_status model=${model}`);
    this.currentModel = model;
  }
}

export { 
  DetailedModelEscalator, 
  FunctionalModelEscalator, 
  EventModelEscalator,
  ModelTier 
};