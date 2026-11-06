import os
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.workers.runner import WorkerRunner
from pipecat.audio.vad.silero import SileroVADAnalyzer

from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService

from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMUserAggregatorParams,LLMContextAggregatorPair

from pipecat.transports.base_transport import BaseTransport,TransportParams
from pipecat.runner.utils import create_transport
from pipecat.runner.types import RunnerArguments
from pipecat.flows import FlowManager

from .agents import agent_node, switch_agent

load_dotenv()

def create_transportParams():
    return TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True
    )


transport_params = {
    "webrtc":create_transportParams
}

async def run_bot(transport:BaseTransport,runner_args:RunnerArguments):
    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY")
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAILLMService.Settings(
            model="gpt-6-luna",
            extra={"reasoning_effort":"none"}
        )
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(
            voice="db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"
        )
    )

    context = LLMContext()

    aggregator = LLMContextAggregatorPair(
        context=context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer()
        )
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        aggregator.user(),
        llm,
        tts,
        transport.output(),
        aggregator.assistant()
    ])

    agent = PipelineWorker(
        name="J.A.R.V.I.S",
        pipeline=pipeline
    )

    flow_manager = FlowManager(
        worker=agent,
        llm=llm,
        context_aggregator=aggregator,
        transport=transport,
        global_functions=[switch_agent]
    )

    @transport.event_handler("on_client_connected")
    async def client_connected(transport, client):
        await flow_manager.initialize(agent_node("General"))

    @transport.event_handler("on_client_disconnected")
    async def client_disconnected(transport, client):
        await runner.cancel()

    await runner.add_workers(agent)
    await runner.run()

async def bot(runner_args:RunnerArguments):
    transport = await create_transport(runner_args,transport_params)
    await run_bot(transport,runner_args)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()

