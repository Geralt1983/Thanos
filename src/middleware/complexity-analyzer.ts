import { 
  ComplexityScore 
} from '../types/escalator';

export class ComplexityAnalyzer {
  /**
   * Analyze the complexity of a conversation
   * @param conversationHistory Full conversation history
   * @returns Comprehensive complexity score
   */
  public analyzeComplexity(conversationHistory: string[]): ComplexityScore {
    const analysis: ComplexityScore = {
      overall: 0,
      cognitive_load: 0,
      technical_depth: 0,
      creativity_level: 0
    };

    // Complexity signals
    const technicalKeywords = [
      'algorithm', 'architecture', 'system design', 'machine learning', 
      'typescript', 'middleware', 'computational', 'complexity'
    ];

    const creativeKeywords = [
      'imagine', 'design', 'create', 'innovate', 'conceptualize', 
      'hypothetical', 'strategy'
    ];

    let technicalTermCount = 0;
    let creativeTermCount = 0;

    // Analyze each message
    conversationHistory.forEach(message => {
      const lowercaseMessage = message.toLowerCase();
      
      // Technical depth
      technicalKeywords.forEach(keyword => {
        if (lowercaseMessage.includes(keyword)) {
          technicalTermCount++;
        }
      });

      // Creativity level
      creativeKeywords.forEach(keyword => {
        if (lowercaseMessage.includes(keyword)) {
          creativeTermCount++;
        }
      });

      // Cognitive load estimation based on message length and complexity
      const wordCount = message.split(/\s+/).length;
      const sentenceComplexity = this.calculateSentenceComplexity(message);

      analysis.cognitive_load += (wordCount * sentenceComplexity) / 100;
    });

    // Normalize and compute scores
    analysis.technical_depth = Math.min(
      (technicalTermCount / conversationHistory.length) * 100, 
      100
    );
    
    analysis.creativity_level = Math.min(
      (creativeTermCount / conversationHistory.length) * 100, 
      100
    );

    // Overall complexity is a weighted combination
    analysis.overall = (
      analysis.technical_depth * 0.4 + 
      analysis.cognitive_load * 0.3 + 
      analysis.creativity_level * 0.3
    );

    return analysis;
  }

  /**
   * Calculate sentence complexity based on structure and linguistic features
   * @param sentence Input sentence
   * @returns Complexity score 0-100
   */
  private calculateSentenceComplexity(sentence: string): number {
    // Linguistic complexity factors
    const clauseCount = (sentence.match(/[,;:]-/g) || []).length + 1;
    const subordinateClauses = (sentence.match(/\b(because|although|while|since|if)\b/gi) || []).length;
    const technicalTerms = (sentence.match(/[A-Z][a-z]+[A-Z][a-z]+/) || []).length;

    let complexity = (
      clauseCount * 10 + 
      subordinateClauses * 15 + 
      technicalTerms * 20
    );

    return Math.min(complexity, 100);
  }
}