import { Agent, Artifact, Composition, Question, preview, taskTemplate } from '../src/index.js';

export class HelloWorldAgent extends Agent {
  @taskTemplate('hello_world')
  prepare(inputs: Record<string, unknown>, ctx: { hasAnswer: (id: string) => boolean; answer: (id: string) => unknown; requestClarification: Function; readyToAuthorize: Function }) {
    const composition = Composition.input([
      Composition.dropdownWithDescriptions('tone', {
        label: 'Tone',
        options: [{ id: 'friendly', label: 'Friendly' }, { id: 'formal', label: 'Formal' }],
        default: 'friendly',
      }),
    ], { taskTemplate: 'hello_world', compositionId: 'hello_world.v1' });
    if (!ctx.hasAnswer('tone')) {
      return ctx.requestClarification([
        Question.singleSelect({
          id: 'tone',
          label: 'Tone',
          options: ['friendly', 'formal'],
          default: 'friendly',
          decideForMe: { value: 'friendly' },
        }),
      ], { compositionResponse: composition });
    }
    return ctx.readyToAuthorize({ normalizedInputs: { name: inputs.name ?? 'there', tone: ctx.answer('tone') }, compositionResponse: composition });
  }

  @preview('hello_world')
  previewHello(inputs: Record<string, unknown>) {
    return { type: 'text', value: `Hello ${inputs.name ?? 'there'}` };
  }

  @taskTemplate('hello_world')
  async run(inputs: Record<string, unknown>, ctx: { stageArtifact: Function }) {
    await ctx.stageArtifact(Artifact.generic({ payload: { message: `Hello ${inputs.name}`, tone: inputs.tone } }));
  }
}
