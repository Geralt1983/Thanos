import { 
  ModelAvailability, 
  EscalationConfig 
} from '../types/escalator';
import axios from 'axios';

export class ModelResolver {
  // List of supported Anthropic models
  private static ANTHROPIC_MODELS = [
    'anthropic/claude-3-haiku-20240307',
    'anthropic/claude-3-5-sonnet-20241022',
    'anthropic/claude-opus-4-5'
  ];

  // In-memory cache of model availability
  private static modelAvailabilityCache: Record<string, ModelAvailability> = {};

  /**
   * Check model availability via API
   * @param modelId Model identifier
   * @returns Model availability information
   */
  public static async checkModelAvailability(modelId: string): Promise<ModelAvailability> {
    // Check cache first
    const cachedAvailability = this.modelAvailabilityCache[modelId];
    const now = Date.now();

    // Use cached result if less than 5 minutes old
    if (cachedAvailability && 
        (now - cachedAvailability.lastAvailabilityCheck) < 5 * 60 * 1000) {
      return cachedAvailability;
    }

    try {
      // Replace with actual OpenClaw model availability API endpoint
      const response = await axios.get(`/api/models/${modelId}/availability`, {
        headers: {
          'Authorization': `Bearer ${process.env.OPENCLAW_API_KEY}`
        }
      });

      const availability: ModelAvailability = {
        modelId,
        available: response.data.available,
        maxTokens: response.data.maxTokens,
        costPer1kInputTokens: response.data.costPer1kInputTokens,
        costPer1kOutputTokens: response.data.costPer1kOutputTokens,
        lastAvailabilityCheck: now
      };

      // Update cache
      this.modelAvailabilityCache[modelId] = availability;

      return availability;
    } catch (error) {
      console.warn(`Model availability check failed for ${modelId}`, error);
      
      // Fallback default availability
      return {
        modelId,
        available: false,
        maxTokens: 0,
        costPer1kInputTokens: 0,
        costPer1kOutputTokens: 0,
        lastAvailabilityCheck: now
      };
    }
  }

  /**
   * Resolve next model in escalation chain
   * @param currentModel Current model in use
   * @param config Escalation configuration
   * @returns Next available model or fallback
   */
  public static async resolveNextModel(
    currentModel: string, 
    config: EscalationConfig
  ): Promise<string> {
    const modelIndex = config.escalationModels.indexOf(currentModel);
    
    // Try next models in the chain
    for (let i = modelIndex + 1; i < config.escalationModels.length; i++) {
      const nextModel = config.escalationModels[i];
      const availability = await this.checkModelAvailability(nextModel);
      
      if (availability.available) {
        return nextModel;
      }
    }

    // Fallback to base model if no alternatives available
    return config.baseModel;
  }
}