import { ModelSwitcher } from '../src/core/model-switcher';
import { ModelEscalatorConfig } from '../src/core/config-schema';

describe('ModelSwitcher', () => {
  const mockConfig: ModelEscalatorConfig = {
    providers: [
      {
        id: 'small-model',
        name: 'Small Model',
        apiKey: 'test-key',
        baseUrl: 'https://small-model.com',
        maxTokens: 1000
      },
      {
        id: 'large-model',
        name: 'Large Model',
        apiKey: 'test-key',
        baseUrl: 'https://large-model.com',
        maxTokens: 50000
      }
    ],
    complexityRules: [
      {
        name: 'High Complexity',
        maxTokens: 5000
      }
    ],
    defaultProvider: 'small-model',
    loggingLevel: 'info',
    performanceThreshold: 500
  };

  let modelSwitcher: ModelSwitcher;

  beforeEach(() => {
    modelSwitcher = new ModelSwitcher(mockConfig);
  });

  test('should select default provider for simple input', () => {
    const selectedModel = modelSwitcher.selectModel('Simple input');
    expect(selectedModel.id).toBe('small-model');
  });

  test('should escalate to larger model for complex input', () => {
    const complexInput = 'a'.repeat(6000);
    const selectedModel = modelSwitcher.selectModel(complexInput);
    expect(selectedModel.id).toBe('large-model');
  });
});