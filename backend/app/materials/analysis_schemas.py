from datetime import UTC, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator

Status = Literal['not_requested', 'pending', 'processing', 'succeeded', 'failed']
ERROR_MESSAGES = {
    'missing_key': 'AI 연결 설정이 필요해요. 파일은 저장됐어요.',
    'invalid_key': 'AI 인증 설정을 확인해 주세요.',
    'model_unavailable': 'AI 모델 접근 설정을 확인해 주세요.',
    'quota_exceeded': 'AI 사용 한도나 결제 상태를 확인해 주세요.',
    'rate_limited': 'AI 요청이 많아요. 잠시 후 다시 시도해 주세요.',
    'timeout': 'AI 응답을 확인하지 못했어요. 재시도 시 추가 비용이 발생할 수 있어요.',
    'network_error': 'AI 연결 결과를 확인하지 못했어요. 재시도 시 추가 비용이 발생할 수 있어요.',
    'unsupported_video': '이 영상의 화면을 분석하지 못했어요. 원본은 유지돼요.',
    'invalid_media': '분석용 이미지를 읽지 못했어요.',
    'preprocessing_limit': '분석 처리 한도를 초과했어요. 원본은 유지돼요.',
    'refused': '이 자료의 요약을 제공하지 못했어요.',
    'invalid_output': '유효한 요약을 만들지 못했어요.',
    'original_missing': '원본 파일 상태를 확인해 주세요.',
    'interrupted': '분석이 중단됐어요. 다시 요약할 수 있어요.',
    'queue_full': '대기 중인 분석이 많아요. 잠시 후 다시 요약해 주세요.',
    'internal_error': '요약 처리 중 문제가 발생했어요.',
}

class AnalysisFailure(Exception):
    def __init__(self, code):
        self.code = code if code in ERROR_MESSAGES else 'internal_error'
        super().__init__(self.code)

class SummaryPayload(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary: str

    @field_validator('summary')
    @classmethod
    def valid_summary(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 2000:
            raise ValueError('Invalid summary length')
        return value

class AnalysisOutput(BaseModel):
    status: Status
    version: int
    summary: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None
    scope: dict | None = None
    attempt_count: int
    can_retry: bool

    @field_validator('completed_at')
    @classmethod
    def utc(cls, value):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value

def public_analysis(material, configured=True):
    code = material.analysis_error_code
    return AnalysisOutput(status=material.analysis_status, version=material.analysis_version,
        summary=material.analysis_summary, error_code=code,
        error_message=ERROR_MESSAGES.get(code) if code else None,
        completed_at=material.analysis_completed_at, scope=material.analysis_metadata,
        attempt_count=material.analysis_attempt_count,
        can_retry=configured and material.analysis_status == 'failed' and material.analysis_attempt_count < 3)
