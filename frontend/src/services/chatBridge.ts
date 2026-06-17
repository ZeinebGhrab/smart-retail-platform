type ChatListener = (message: string) => void;
let _listener: ChatListener | null = null;
let _pending: string | null = null;

export function registerChatListener(fn: ChatListener) {
  console.log('[Bridge] registerChatListener called');
  _listener = fn;
  if (_pending) {
    console.log('[Bridge] flushing pending message:', _pending.slice(0, 50));
    fn(_pending);
    _pending = null;
  }
}

export function unregisterChatListener() {
  console.log('[Bridge] unregisterChatListener called');
  _listener = null;
}

export function sendToChat(message: string) {
  console.log('[Bridge] sendToChat called, listener=', !!_listener, 'msg=', message.slice(0, 50));
  if (_listener) {
    _listener(message);
  } else {
    console.log('[Bridge] no listener → storing as pending');
    _pending = message;
  }
}

export function debugBridge() {
  console.log('[Bridge] state → listener:', !!_listener, '| pending:', _pending?.slice(0, 50) ?? 'null');
}