# custom callbacks for pjsua2

import pjsua2 as pj


class Call(pj.Call):
    def __init__(self, acc, call_id=pj.PJSUA_INVALID_ID):
        super().__init__(acc, call_id)
        self.info_changed = False
        self.media_changed = False
        self.last_info = None
        self.last_prm = None

    def onCallState(self, prm):
        """Invoked with call state changes in SIP."""
        self.info_changed = True
        self.last_prm = prm
        return super().onCallState(prm)

    def onCallMediaState(self, prm):
        """Invoked upon call media consent between caller and callee."""
        self.media_changed = True
        self.last_prm = prm
        return super().onCallMediaState(prm)

    def getInfo(self):
        """clear flags and do its regular behavior."""
        self.info_changed = False
        self.last_info = super().getInfo()
        return self.last_info


class Account(pj.Account):
    def __init__(self):
        super().__init__()
        self._call = None
        self._call_op_param = None

    def onIncomingCall(self, prm):
        """Handle incoming call."""
        call = Call(self, call_id=prm.callId)
        call_prm = pj.CallOpParam(True)
        call_prm.statusCode = pj.PJSIP_SC_OK
        call.answer(call_prm)
        self._call = call
        self._call_op_param = call_prm
        return super().onIncomingCall(prm)
