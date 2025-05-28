# custom callbacks for pjsua2

import pjsua2 as pj


class Call(pj.Call):
    def __init__(self, acc, call_id=pj.PJSUA_INVALID_ID):
        super().__init__(acc, call_id)
        self._delete_call = False

    def onCallState(self, prm):
        """Invoked with call state changes in SIP."""
        if self.getInfo().state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self._delete_call = True


class Account(pj.Account):
    def __init__(self):
        super().__init__()
        self._call = None

    def onIncomingCall(self, prm):
        call = Call(self, call_id=prm.callId)
        call_prm = pj.CallOpParam(True)
        call_prm.statusCode = pj.PJSIP_SC_OK
        call.answer(call_prm)
        self._call = call
        return super().onIncomingCall(prm)
