import pytest
from pydantic import ValidationError
from backend.app.audio import normalize_audio
from backend.app.providers import FasterWhisperProvider, LLMExtractionProvider, ProcessingError, validate_evidence
from backend.app.schemas import Extraction
from tests.conftest import TestExtractionProvider, TestSpeechProvider, TEST_TEXT
from backend.app.providers import TranscriptionResult


def test_missing_model_is_actionable(settings, tmp_path):
    with pytest.raises(ProcessingError, match='download_model.py') as exc:
        FasterWhisperProvider(settings).transcribe(tmp_path/'unused.wav', 'en')
    assert exc.value.code == 'MODEL_MISSING'


def test_normalization_checks_real_duration(tmp_path, wav_bytes):
    source, destination = tmp_path/'audio', tmp_path/'pcm.wav'
    source.write_bytes(wav_bytes(2))
    assert normalize_audio(source, destination, 3) == 2
    import wave
    with wave.open(str(destination)) as wav:
        assert (wav.getnchannels(),wav.getframerate(),wav.getsampwidth()) == (1,16000,2)
    with pytest.raises(ProcessingError) as exc:
        normalize_audio(source, destination, 1)
    assert exc.value.code == 'DURATION_LIMIT'
    assert not destination.exists()


@pytest.mark.parametrize('payload,code', [(b'corrupted-data','INVALID_AUDIO'), (b'','INVALID_AUDIO')])
def test_corrupted_audio(tmp_path,payload,code):
    source=tmp_path/'source';source.write_bytes(payload)
    with pytest.raises(ProcessingError) as exc:
        normalize_audio(source,tmp_path/'pcm.wav',10)
    assert exc.value.code == code


def test_silence(tmp_path,wav_bytes):
    source=tmp_path/'source';source.write_bytes(wav_bytes(silent=True))
    with pytest.raises(ProcessingError) as exc:
        normalize_audio(source,tmp_path/'pcm.wav',10)
    assert exc.value.code == 'NO_SPEECH'
    assert not exc.value.retryable


def extraction():
    transcript = TranscriptionResult(TEST_TEXT,[{'text':TEST_TEXT,'start':0,'end':3}], 'en','TEST_DOUBLE','TEST_ONLY')
    return transcript, TestExtractionProvider().extract(transcript,'restaurant',[])


def test_evidence_is_exact_and_segment_linked():
    transcript,result=extraction()
    assert validate_evidence(result,transcript,[]) is result
    result.insights[0].evidence[0].quote='A quote nobody said'
    with pytest.raises(ProcessingError) as exc:validate_evidence(result,transcript,[])
    assert exc.value.code=='EVIDENCE_INVALID'


def test_invalid_segment_rejected():
    transcript,result=extraction();result.insights[0].evidence[0].segment_index=20
    with pytest.raises(ProcessingError):validate_evidence(result,transcript,[])


def test_unconfigured_categories_rejected():
    transcript,result=extraction();result.insights[0].category='fabricated_category'
    with pytest.raises(ProcessingError):validate_evidence(result,transcript,[])
    assert validate_evidence(result,transcript,['fabricated_category'])


@pytest.mark.parametrize('change', ['confidence','missing_evidence','invalid_action'])
def test_extraction_schema_rejects_bad_output(change):
    _,result=extraction();data=result.model_dump()
    if change=='confidence':data['insights'][0]['confidence']=1.8
    if change=='missing_evidence':data['insights'][0]['evidence']=[]
    if change=='invalid_action':data['actions'][0]['insight_index']=3
    with pytest.raises(ValidationError):Extraction.model_validate(data)


def test_cloud_never_enabled_implicitly(settings):
    settings.llm_base_url='https://remote.example.test/v1'
    with pytest.raises(ValueError,match='ALLOW_CLOUD'):LLMExtractionProvider(settings)
    settings.allow_cloud=True;settings.llm_base_url='http://remote.example.test/v1'
    with pytest.raises(ValueError,match='HTTPS'):LLMExtractionProvider(settings)


def test_unavailable_ai_provider_is_real_failure(settings):
    settings.llm_base_url='http://127.0.0.1:1'
    transcript,_=extraction()
    with pytest.raises(ProcessingError) as exc:LLMExtractionProvider(settings).extract(transcript,'restaurant',[])
    assert exc.value.code=='AI_UNAVAILABLE'


@pytest.mark.parametrize('provider',['ollama','openai_compatible'])
def test_llm_http_structured_output_contract(settings,monkeypatch,provider):
    import json,httpx
    transcript,result=extraction()
    settings.extraction_provider=provider
    original_client=httpx.Client
    requests=[]
    def handle(request):
        requests.append(request)
        payload=json.loads(request.content)
        assert payload['model']==settings.llm_model
        if provider=='ollama':
            assert payload['format']['type']=='object'
            return httpx.Response(200,json={'message':{'content':result.model_dump_json()}})
        assert payload['response_format']['type']=='json_schema'
        return httpx.Response(200,json={'choices':[{'message':{'content':result.model_dump_json()}}]})
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original_client(transport=httpx.MockTransport(handle)))
    actual=LLMExtractionProvider(settings).extract(transcript,'restaurant',[])
    assert actual.summary==result.summary
    assert requests[0].url.path==('/api/chat' if provider=='ollama' else '/chat/completions')


def test_malformed_llm_output_is_not_an_insight(settings,monkeypatch):
    import httpx
    transcript,_=extraction();original_client=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original_client(transport=httpx.MockTransport(
        lambda request:httpx.Response(200,json={'message':{'content':'{"not_the_schema":true}'}}))))
    with pytest.raises(ProcessingError) as exc:LLMExtractionProvider(settings).extract(transcript,'retail',[])
    assert exc.value.code=='EXTRACTION_INVALID'


def test_llm_segment_numbers_are_grounded_from_exact_quotes():
    from backend.app.providers import ground_evidence
    transcript,result=extraction()
    result.insights[0].evidence[0].segment_index=99
    actual=ground_evidence(result,transcript,[])
    assert actual.insights[0].evidence[0].segment_index==0


def test_ambiguous_quote_does_not_claim_a_timestamp():
    from backend.app.providers import ground_evidence
    transcript,result=extraction()
    transcript.segments.append(dict(transcript.segments[0]))
    assert ground_evidence(result,transcript,[]).insights[0].evidence[0].segment_index is None


def test_grounding_still_rejects_a_fabricated_quote():
    from backend.app.providers import ground_evidence
    transcript,result=extraction()
    result.insights[0].evidence[0].quote='A sentence that nobody spoke.'
    with pytest.raises(ProcessingError) as exc:ground_evidence(result,transcript,[])
    assert exc.value.code=='EVIDENCE_INVALID'


def test_ollama_controls_and_source_grounding_contract(settings,monkeypatch):
    import json,httpx
    transcript,result=extraction();result.insights[0].evidence[0].segment_index=99
    settings.llm_think=False
    original_client=httpx.Client
    def handle(request):
        payload=json.loads(request.content)
        assert payload['think'] is False
        defs=payload['format']['$defs']
        assert 'product_request' in defs['InsightInput']['properties']['category']['enum']
        assert defs['EvidenceInput']['properties']['segment_index']['type']=='null'
        return httpx.Response(200,json={'message':{'content':result.model_dump_json()}})
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original_client(transport=httpx.MockTransport(handle)))
    actual=LLMExtractionProvider(settings).extract(transcript,'retail',[])
    assert actual.insights[0].evidence[0].segment_index==0
