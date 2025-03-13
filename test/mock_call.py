import time
from argparse import ArgumentParser

import pjsua2 as pj
import soundfile as sf

MAX_RING_TIME = 15


class Call(pj.Call):
    def __init__(self, acc):
        pj.Call.__init__(self, acc)
        self.state_changed = False

    def onCallState(self, prm):
        self.state_changed = True

    def onCallMediaState(self, prm):
        for i in range(10):
            print("*" * 80)

    def getInfo(self):
        self.state_changed = False
        return super().getInfo()


def call_amd_agent(
    domain,
    src_username,
    src_password,
    dst_username,
    playback_filename,
):
    # Create and initialize the library
    ep = pj.Endpoint()
    ep.libCreate()

    # configure endpoint
    ep_cfg = pj.EpConfig()
    ep.libInit(ep_cfg)
    ep.audDevManager().setNullDev()

    # configure endpoint transport
    sipTpConfig = pj.TransportConfig()
    ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sipTpConfig)

    # Start the library
    ep.libStart()

    # create account config
    acfg = pj.AccountConfig()
    acfg.idUri = f"sip:{src_username}@{domain}"
    acfg.regConfig.registrarUri = f"sip:{domain}"

    # create authentication config
    cred = pj.AuthCredInfo("digest", "*", src_username, 0, src_password)
    acfg.sipConfig.authCreds.append(cred)

    # Create the account
    acc = pj.Account()
    acc.create(acfg)
    time.sleep(1)

    ########
    # call #
    ########
    call_op_param = pj.CallOpParam(True)
    call = Call(acc)
    call.makeCall(f"sip:{dst_username}@{domain}", call_op_param)

    # wait until MAX_RING_TIME
    call_established = False
    t0 = time.time()
    infos = []
    while time.time() - t0 < MAX_RING_TIME:
        if call.state_changed:
            call_info = call.getInfo()
            infos.append(call_info)
            if call_info.state == pj.PJSIP_INV_STATE_CONFIRMED:
                call_established = True
                break
    call_id = call.getInfo().callIdString
    # sleep time must be bigger than network delay
    time.sleep(0.5)
    if call_established:
        # audio recorder
        wav_writer = pj.AudioMediaRecorder()
        wav_writer.createRecorder(f"/tmp/ztmp-{call_id}.wav")

        # get audio media
        aud_med = call.getAudioMedia(0)
        aud_med.startTransmit(wav_writer)

        # audio player
        player = pj.AudioMediaPlayer()
        player.createPlayer(playback_filename, pj.PJMEDIA_FILE_NO_LOOP)
        player.startTransmit(aud_med)

        # wait till the end of playback
        x, fs = sf.read(playback_filename)
        time.sleep(x.shape[0] / fs)
        try:
            player.stopTransmit(aud_med)
        except:
            pass
        time.sleep(5)
        try:
            call.hangup(call_op_param)
        except:
            pass

    print("*" * 100)
    del call
    del call_op_param
    try:
        del player
    except:
        pass
    # Destroy the library
    ep.libDestroy()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--domain", type=str, default="127.0.0.1")
    parser.add_argument("--src-user", type=str, default="7400")
    parser.add_argument("--src-pass", type=str, default="pass7400")
    parser.add_argument("--dst-num", type=str, default="8500")
    parser.add_argument("--playback-file", type=str, default="George-crop2.wav")
    args = parser.parse_args()

    call_amd_agent(
        domain=args.domain,
        src_username=args.src_user,
        src_password=args.src_pass,
        dst_username=args.dst_num,
        playback_filename=args.playback_file,
    )
