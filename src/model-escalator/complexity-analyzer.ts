import { ModelComplexityScore, ModelComplexityLevel } from './types';

export class ComplexityAnalyzer {
  private static TOKEN_WEIGHT = 0.3;
  private static CONTEXT_WEIGHT = 0.25;
  private static SEMANTIC_WEIGHT = 0.25;
  private static LANGUAGE_WEIGHT = 0.2;

  static async analyzeComplexity(input: string): Promise<ModelComplexityScore> {
    const tokenCount = this.countTokens(input);
    const contextDepth = this.estimateContextDepth(input);
    const semanticComplexity = await this.calculateSemanticComplexity(input);
    const languageSpecificity = this.determineLanguageSpecificity(input);

    const score = this.calculateOverallComplexityScore({
      tokenCount,
      contextDepth,
      semanticComplexity,
      languageSpecificity
    });

    return {
      score,
      factors: {
        tokenCount,
        contextDepth,
        semanticComplexity,
        languageSpecificity
      }
    };
  }

  private static countTokens(input: string): number {
    // Simple token approximation - can be replaced with more sophisticated tokenization
    return input.split(/\s+/).length;
  }

  private static estimateContextDepth(input: string): number {
    // Estimate context complexity based on input structure
    const paragraphCount = input.split('\n\n').length;
    const sentenceComplexity = input.split(/[.!?]/).filter(s => s.trim().length > 10).length;
    return Math.min(10, paragraphCount + sentenceComplexity);
  }

  private static async calculateSemanticComplexity(input: string): Promise<number> {
    // Placeholder for more advanced semantic analysis
    // Could integrate with NLP libraries or machine learning models
    const uniqueWords = new Set(input.toLowerCase().match(/\b\w+\b/g) || []);
    return Math.min(10, uniqueWords.size / 50);
  }

  private static determineLanguageSpecificity(input: string): number {
    // Detect language complexity and specificity
    const technicalTerms = input.match(/[A-Z][a-z]*[A-Z][a-zA-Z]*/g) || [];
    const codeLikeStructures = input.match(/[{};()[\]]/g) || [];
    return Math.min(10, technicalTerms.length + codeLikeStructures.length);
  }

  private static calculateOverallComplexityScore(factors: {
    tokenCount: number;
    contextDepth: number;
    semanticComplexity: number;
    languageSpecificity: number;
  }): number {
    const { tokenCount, contextDepth, semanticComplexity, languageSpecificity } = factors;

    const weightedScore = 
      (tokenCount * this.TOKEN_WEIGHT) +
      (contextDepth * this.CONTEXT_WEIGHT) +
      (semanticComplexity * this.SEMANTIC_WEIGHT) +
      (languageSpecificity * this.LANGUAGE_WEIGHT);

    return Math.min(10, Math.max(0, weightedScore));
  }

  static determineComplexityLevel(score: number): ModelComplexityLevel {
    if (score < 3) return ModelComplexityLevel.LOW;
    if (score < 7) return ModelComplexityLevel.MEDIUM;
    return ModelComplexityLevel.HIGH;
  }
}