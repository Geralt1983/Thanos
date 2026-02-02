import { Plugin, PluginContext } from 'openclaw';
import { z } from 'zod';
import { ModelEscalatorConfigSchema, ModelEscalatorConfig } from './schema';
import { ModelEscalator } from './escalator';

export class ModelEscalatorPlugin implements Plugin {
  private config: ModelEscalatorConfig;
  private modelEscalator: ModelEscalator;

  // Plugin metadata
  static metadata = {
    name: 'model-escalator',
    version: '1.0.0',
    description: 'Intelligent model escalation and de-escalation plugin',
    author: 'OpenClaw Team',
    dependencies: ['session', 'provider']
  };

  // Initialize plugin
  async init(context: PluginContext) {
    // Load configuration
    this.config = context.config.get('session.modelEscalator', 
      ModelEscalatorConfigSchema.parse({})
    );

    // Create ModelEscalator instance
    this.modelEscalator = new ModelEscalator(this.config);

    // Hook into session lifecycle
    context.events.on('session:start', this.onSessionStart.bind(this));
    context.events.on('message:before-process', this.onBeforeMessageProcess.bind(this));
  }

  // Session start handler
  private async onSessionStart(sessionContext: any) {
    // Initialize model escalator for the session
    sessionContext.modelEscalator = this.modelEscalator;
  }

  // Pre-processing message hook
  private async onBeforeMessageProcess(messageContext: any) {
    const { session, message } = messageContext;

    // Skip if plugin is disabled
    if (!this.config.enabled) return;

    // Analyze conversation complexity
    const shouldEscalate = this.modelEscalator.shouldEscalateModel({
      messages: session.messages,
      tokenUsage: session.tokenUsage,
      taskType: session.taskType,
      previousModelUsed: session.currentModel
    });

    const shouldDeescalate = this.modelEscalator.shouldDeescalateModel({
      messages: session.messages,
      tokenUsage: session.tokenUsage,
      taskType: session.taskType,
      previousModelUsed: session.currentModel
    });

    // Trigger model switch if needed
    if (shouldEscalate || shouldDeescalate) {
      const newModel = this.modelEscalator.getCurrentModel();
      
      // Use OpenClaw's provider API to switch models
      await messageContext.context.providers.switchModel(newModel);

      // Log model switch event
      messageContext.context.events.emit('model:switched', {
        fromModel: session.currentModel,
        toModel: newModel,
        reason: shouldEscalate ? 'escalation' : 'de-escalation'
      });
    }
  }

  // Extend session configuration schema
  static extendSchema(baseSchema: z.ZodObject<any>) {
    return baseSchema.extend({
      modelEscalator: ModelEscalatorConfigSchema
    });
  }
}

// Export the plugin
export default ModelEscalatorPlugin;