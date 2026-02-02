import { ComplexityScorer } from './types';

export class DefaultComplexityScorer implements ComplexityScorer {
  calculateComplexity(input: string): number {
    // Multi-dimensional complexity scoring
    const complexityFactors = [
      this.calculateLengthComplexity(input),
      this.calculateLanguageComplexity(input),
      this.calculateStructureComplexity(input)
    ];

    // Average complexity with weight
    return this.normalizeComplexity(
      complexityFactors.reduce((a, b) => a + b, 0) / complexityFactors.length
    );
  }

  private calculateLengthComplexity(input: string): number {
    const length = input.length;
    // Logarithmic scaling of length complexity
    return Math.min(10, Math.log(length + 1) / Math.log(1000));
  }

  private calculateLanguageComplexity(input: string): number {
    // Assess linguistic complexity
    const technicalTerms = input.match(/[A-Z]{2,}|[a-z]+[A-Z][a-z]+/g)?.length || 0;
    const sentenceComplexity = input.split(/[.!?]/).filter(s => s.trim().length > 20).length;

    return Math.min(10, (technicalTerms * 0.5 + sentenceComplexity * 0.3));
  }

  private calculateStructureComplexity(input: string): number {
    // Check for structural complexity markers
    const bracketDepth = (input.match(/[{[()}\]]/g) || []).length;
    const conditionalStatements = (input.match(/if\s*\(|switch\s*\(|for\s*\(|while\s*\(/g) || []).length;

    return Math.min(10, bracketDepth * 0.2 + conditionalStatements * 0.5);
  }

  private normalizeComplexity(rawComplexity: number): number {
    // Final normalization to 0-10 scale
    return Math.max(0, Math.min(10, rawComplexity));
  }
}