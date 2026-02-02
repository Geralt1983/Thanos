import { ModelEscalator } from '../src/model-escalator';
import { ModelEscalatorConfigSchema } from '../src/types';
import exampleConfig from '../example-config.json';

describe('ModelEscalator', () => {
  let modelEscalator: ModelEscalator;

  beforeAll(() => {
    const validatedConfig = ModelEscalatorConfigSchema.parse(exampleConfig);
    modelEscalator = new ModelEscalator(validatedConfig);
  });

  test('should process request and select appropriate model', async () => {
    const simpleRequest = { input: "Hello, world!" };
    const complexRequest = { 
      input: "Develop a comprehensive architectural design for a distributed system with multiple microservices, focusing on scalability, fault tolerance, and optimal performance under high load conditions." 
    };

    const simpleResult = await modelEscalator.processRequest(simpleRequest);
    const complexResult = await modelEscalator.processRequest(complexRequest);

    expect(simpleResult.modelUsed).toBe("Claude Haiku");
    expect(complexResult.modelUsed).toBe("Claude Opus");
    expect(simpleResult.complexity).toBeLessThan(complexResult.complexity);
  });

  test('complexity scorer handles different input types', () => {
    const scorer = modelEscalator['complexityScorer'];
    
    const simpleSentence = scorer.calculateComplexity("Hello world");
    const technicalText = scorer.calculateComplexity("Implement a recursive depth-first search algorithm with O(n) time complexity");
    const codeLikeInput = scorer.calculateComplexity("function complexAlgorithm() { if (condition) { return deepNestedLogic(); } }");

    expect(simpleSentence).toBeLessThan(technicalText);
    expect(technicalText).toBeLessThan(codeLikeInput);
  });

  test('model selection respects configuration', async () => {
    const requests = [
      { complexity: 2, expectedModel: "Claude Haiku" },
      { complexity: 5, expectedModel: "Claude Sonnet" },
      { complexity: 9, expectedModel: "Claude Opus" }
    ];

    for (const request of requests) {
      const result = await modelEscalator['processRequest']({ 
        input: "x".repeat(request.complexity * 100) 
      });
      expect(result.modelUsed).toBe(request.expectedModel);
    }
  });
});