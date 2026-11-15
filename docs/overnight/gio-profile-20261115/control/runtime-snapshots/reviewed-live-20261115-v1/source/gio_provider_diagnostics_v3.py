"""Future execution-envelope observer. No retries, body/header/message logging or wire edits.
Install once around a process's provider work; do not nest observers. Forward the
same Request object, timeout, read bytes, context-manager behavior and exceptions.
An explicit denylist can prevent dispatch; accounting/authorization stay upstream.
"""
import hashlib,json,re,threading,time,urllib.error,urllib.request
from contextlib import contextmanager
from datetime import datetime,timezone
VERSION='provider-boundary-diagnostics-v3'
BODY_IDENTITY='body_compact_json_sha256'
ENDPOINT_IDENTITY='endpoint_body_sorted_json_sha256'
_lock=threading.RLock()
_installed=False

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def safe_request_id(headers):
    try:value=headers.get('x-request-id') if headers is not None else None
    except Exception:return None
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',value):return None
    return sha(value.encode('utf-8'))

class ObservationState:
    def __init__(self):
        self.diagnostic_write_failed=False
        self.dropped_event_count=0
    def summary(self):
        return {'diagnostic_write_failed':self.diagnostic_write_failed,'dropped_event_count':self.dropped_event_count}

class DiagnosticWriteFailure(RuntimeError):
    pass

def exception_type(exc):
    for cls in (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ConnectionError,OSError,ValueError):
        if isinstance(exc,cls):return cls.__name__
    return 'other'

def request_metadata(request):
    raw=getattr(request,'data',None)
    meta={'wire_bytes_sha256':sha(raw) if isinstance(raw,bytes) else None,'request_sha256':None,'endpoint_body_sha256':None}
    if isinstance(raw,bytes):
        try:
            body=json.loads(raw)
            meta['request_sha256']=sha(canonical(body).encode('utf-8'))
            endpoint=getattr(request,'full_url',None)
            if isinstance(endpoint,str):
                # Frozen reference forensic identity uses sorted default separators.
                meta['endpoint_body_sha256']=sha(json.dumps({'endpoint':endpoint,'body':body},ensure_ascii=False,sort_keys=True).encode('utf-8'))
        except (ValueError,TypeError,UnicodeError):pass
    return meta

def status_of(response):
    status=getattr(response,'status',None)
    return status if type(status) is int and 100<=status<=599 else None

class ResponseProxy:
    def __init__(self,response,emit):self.response,self.emit=response,emit
    def __getattr__(self,name):return getattr(self.response,name)
    def __enter__(self):
        entered=self.response.__enter__()
        return self if entered is self.response else ResponseProxy(entered,self.emit)
    def __exit__(self,*args):return self.response.__exit__(*args)
    def read(self,*args,**kwargs):
        try:return self.response.read(*args,**kwargs)
        except BaseException as exc:
            self.emit('read',exc,self.response)
            raise

@contextmanager
def observe(sink,*,opener=None,denylist=(),identity_denylists=None):
    global _installed
    named=identity_denylists or {}
    if not isinstance(named,dict) or set(named)-{BODY_IDENTITY,ENDPOINT_IDENTITY}:raise ValueError('unsupported_identity_convention')
    body_blocked=frozenset(named.get(BODY_IDENTITY,()))
    endpoint_blocked=frozenset(named.get(ENDPOINT_IDENTITY,()))
    with _lock:
        if _installed:raise ValueError('diagnostic_observer_already_installed')
        _installed=True
    original=urllib.request.urlopen;underlying=opener or original;blocked=frozenset(denylist);state=ObservationState()
    def wrapped(request,*args,**kwargs):
        if state.diagnostic_write_failed:raise DiagnosticWriteFailure('prior_diagnostic_write_failed_no_new_transport')
        start=time.monotonic();meta=request_metadata(request)
        timeout=kwargs.get('timeout',args[0] if args else None)
        if not isinstance(timeout,(int,float)) or isinstance(timeout,bool):timeout=None
        def emit(stage,exc=None,response=None):
            code=status_of(response) if response is not None else None
            headers=getattr(response,'headers',None) if response is not None else None
            if isinstance(exc,urllib.error.HTTPError):
                code=exc.code if type(exc.code) is int and 100<=exc.code<=599 else None
                headers=exc.headers
            event=dict(meta,schema_version=VERSION,stage=stage,at_utc=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=time.monotonic()-start,timeout_seconds=timeout,http_status=code,
                exception_type=exception_type(exc) if exc is not None else None,provider_request_id_sha256=safe_request_id(headers))
            with _lock:
                try:sink(event)
                except Exception:
                    state.diagnostic_write_failed=True
                    state.dropped_event_count+=1
        if (meta['request_sha256'] in blocked|body_blocked or
                meta['endpoint_body_sha256'] in blocked|endpoint_blocked):
            emit('denied_before_transport',ValueError())
            raise ValueError('request_identity_denied_no_dispatch')
        try:response=underlying(request,*args,**kwargs)
        except BaseException as exc:
            emit('open',exc)
            raise
        emit('open',response=response)
        return ResponseProxy(response,emit)
    urllib.request.urlopen=wrapped
    try:yield state
    finally:
        urllib.request.urlopen=original
        with _lock:_installed=False
