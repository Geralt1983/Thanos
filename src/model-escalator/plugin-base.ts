import { ModelEscalatorPlugin, ModelComplexityScore } from './types';
import { ModelConfig } from '../core/config';

export abstract class BaseModelEscalatorPlugin implements ModelEscalatorPlugin {
  name: string;

  constructor(name: string) {
    this.name = name;
  }

  abstract analyze(input: string): Promise<ModelComplexityScore>;
  
  abstract selectAppropriateModel(complexityScore: ModelComplexityScore): Promise<ModelConfig>;

  // Optional utility methods for plugin development
  protected normalizeScore(score: number): number {
    return Math.min(10, Math.max(0, score));
  }

  protected logPluginEvent(event: string, details: Record<string, any>) {
    console.log(`[${this.name}] ${event}`, details);
  }
}

// Example implementation of a specialized plugin
export class DomainSpecificModelPlugin extends BaseModelEscalatorPlugin {
  private domainKeywords: { [key: string]: string };

  constructor(name: string, domainKeywords: { [key: string]: string }) {
    super(name);
    this.domainKeywords = domainKeywords;
  }

  async analyze(input: string): Promise<ModelComplexityScore> {
    let domainScore = 0;
    
    for (const [domain, keywords] of Object.entries(this.domainKeywords)) {
      const keywordMatches = input.toLowerCase().match(new RegExp(keywords, 'g')) || [];
      domainScore += keywordMatches.length;
    }

    return {
      score: this.normalizeScore(domainScore),
      factors: {
        tokenCount: input.split(/\s+/).length,
        contextDepth: input.split('\n').length,
        semanticComplexity: domainScore,
        languageSpecificity: 0
      }
    };
  }

  async selectAppropriateModel(complexityScore: ModelComplexityScore): Promise<ModelConfig> {
    // Example domain-specific model selection logic
    if (complexityScore.score > 7) {
      return { 
        name: `advanced-${this.name}-model`,
        maxTokens: 32000,
        contextWindow: 128000
      };
    }

    return {
      name: `standard-${this.name}-model`,
      maxTokens: 16000,
      contextWindow: 64000
    };
  }
}