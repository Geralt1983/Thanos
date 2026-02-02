import { ComplexityDetector } from './complexity-detector';
import { ModelProvider, ModelEscalatorConfig } from './config-schema';
import { Logger } from '../utils/logger';

export class ModelSwitcher {
  private providers: ModelProvider[];
  private complexityDetector: ComplexityDetector;
  private defaultProvider: string;
  private logger: Logger;

  constructor(config: ModelEscalatorConfig) {
    this.providers = config.providers;
    this.complexityDetector = new ComplexityDetector(config.complexityRules);
    this.defaultProvider = config.defaultProvider;
    this.logger = new Logger('ModelSwitcher');
  }

  /**
   * Select the most appropriate model based on input complexity
   * @param input - The input text to analyze
   * @returns Selected model provider
   */
  selectModel(input: string): ModelProvider {
    const complexityResult = this.complexityDetector.detectComplexity(input);

    if (complexityResult.isComplex && complexityResult.rule) {
      this.logger.info(`Complex input detected. Escalating model selection.`);
      
      // Find a provider with higher capability
      const escalatedProvider = this.findEscalatedProvider(
        complexityResult.rule.maxTokens
      );

      return escalatedProvider || this.getDefaultProvider();
    }

    return this.getDefaultProvider();
  }

  private findEscalatedProvider(maxTokens: number): ModelProvider | null {
    const suitableProviders = this.providers
      .filter(provider => 
        provider.maxTokens && provider.maxTokens >= maxTokens
      )
      .sort((a, b) => (a.maxTokens || 0) - (b.maxTokens || 0));

    return suitableProviders[0] || null;
  }

  private getDefaultProvider(): ModelProvider {
    const provider = this.providers.find(p => p.id === this.defaultProvider);
    
    if (!provider) {
      this.logger.error(`Default provider ${this.defaultProvider} not found!`);
      throw new Error('No valid default provider configured');
    }

    return provider;
  }
}