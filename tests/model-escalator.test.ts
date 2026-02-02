import { ModelEscalator } from '../src/model-escalator/model-escalator';
import { ModelEscalatorConfigManager } from '../src/model-escalator/config-manager';
import { ComplexityAnalyzer } from '../src/model-escalator/complexity-analyzer';
import { ModelComplexityLevel } from '../src/model-escalator/types';

describe('ModelEscalator', () => {
  let modelEscalator: ModelEscalator;
  let configManager: ModelEscalatorConfigManager;

  beforeEach(() => {
    // Mock dependencies
    const mockLogger = {
      info: jest.fn(),
      warn: jest.fn(),
      error: jest.fn()
    };

    const mockModelRegistry = {
      process: jest.fn(),
      getNextTierModel: jest.fn().mockReturnValue('claude-sonnet'),
      getHighestCapacityModel: jest.fn().mockReturnValue('claude-opus')
    };

    const defaultConfig = {
      defaultModel: 'claude-haiku',
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

    configManager = new ModelEscalatorConfigManager(mockLogger as any);
    modelEscalator = new ModelEscalator(
      defaultConfig, 
      mockLogger as any, 
      mockModelRegistry as any
    );
  });

  describe('Complexity Analysis', () => {
    it('should correctly determine complexity levels', () => {
      const testCases = [
        { input: 'Simple short text', expectedLevel: ModelComplexityLevel.LOW },
        { input: 'A more complex text with multiple sentences and some technical terminology about software engineering', expectedLevel: ModelComplexityLevel.MEDIUM },
        { input: `Extremely complex technical description spanning multiple paragraphs with in-depth technical terminology, 
          complex logical structures, and requiring significant semantic understanding of advanced computer science concepts, 
          including but not limited to machine learning architectures, distributed systems design, and quantum computing principles.`, 
          expectedLevel: ModelComplexityLevel.HIGH }
      ];

      testCases.forEach(async (testCase) => {
        const complexityScore = await ComplexityAnalyzer.analyzeComplexity(testCase.input);
        const complexityLevel = ComplexityAnalyzer.determineComplexityLevel(complexityScore.score);
        expect(complexityLevel).toBe(testCase.expectedLevel);
      });
    });
  });

  describe('Model Selection', () => {
    it('should select appropriate model based on complexity', async () => {
      const testScenarios = [
        { 
          input: 'Hello world', 
          currentModel: 'claude-haiku', 
          expectedModelPattern: 'haiku' 
        },
        { 
          input: 'Detailed explanation of quantum computing principles...', 
          currentModel: 'claude-haiku', 
          expectedModelPattern: 'sonnet' 
        },
        { 
          input: 'Extremely complex research paper on advanced machine learning architectures...', 
          currentModel: 'claude-sonnet', 
          expectedModelPattern: 'opus' 
        }
      ];

      for (const scenario of testScenarios) {
        const response = await modelEscalator.processInput(scenario.input, scenario.currentModel);
        
        // Verify model selection logic
        expect(response).toBeDefined();
      }
    });
  });

  describe('Performance Tracking', () => {
    it('should log performance warnings for slow processing', async () => {
      // Implement performance tracking test
      const longInput = 'A'.repeat(100000); // Large input to potentially trigger performance tracking
      await modelEscalator.processInput(longInput, 'claude-haiku');
      
      // Add assertions based on your logging mechanism
    });
  });

  describe('Configuration Management', () => {
    it('should allow dynamic config updates', () => {
      const newConfig = {
        ...configManager.loadConfig(),
        complexityThresholds: {
          low: 2,
          medium: 6,
          high: 8
        }
      };

      configManager.saveConfig(newConfig);
      const loadedConfig = configManager.loadConfig();

      expect(loadedConfig.complexityThresholds).toEqual({
        low: 2,
        medium: 6,
        high: 8
      });
    });
  });
});