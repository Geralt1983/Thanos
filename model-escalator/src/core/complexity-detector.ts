import { ComplexityRule } from './config-schema';

export class ComplexityDetector {
  private rules: ComplexityRule[];

  constructor(rules: ComplexityRule[]) {
    this.rules = rules;
  }

  /**
   * Determine the complexity of a given input
   * @param input - The text to analyze
   * @returns Complexity level and matching rule
   */
  detectComplexity(input: string): { 
    isComplex: boolean; 
    rule?: ComplexityRule 
  } {
    const tokens = this.tokenize(input);
    
    for (const rule of this.rules) {
      if (this.meetsComplexityCriteria(tokens, rule)) {
        return { 
          isComplex: true, 
          rule 
        };
      }
    }

    return { isComplex: false };
  }

  private tokenize(input: string): string[] {
    // Simple tokenization - can be replaced with more sophisticated tokenizers
    return input.split(/\s+/);
  }

  private meetsComplexityCriteria(
    tokens: string[], 
    rule: ComplexityRule
  ): boolean {
    // Check total token count
    if (tokens.length > rule.maxTokens) {
      return true;
    }

    // Optional: Check for special tokens or context complexity
    if (rule.minSpecialTokens) {
      const specialTokens = tokens.filter(token => 
        /[^a-zA-Z0-9\s]/.test(token)
      );
      if (specialTokens.length >= rule.minSpecialTokens) {
        return true;
      }
    }

    return false;
  }
}