import multiprocessing
import random
import time
from argparse import ArgumentParser
from pathlib import Path

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
    # del call
    try:
        del call
    except:
        pass
    # del call_op_param
    try:
        del call_op_param
    except:
        pass
    try:
        del player
    except:
        pass
    # Destroy the library
    try:
        ep.libDestroy()
    except:
        pass


def call_amd_agent_wrapper(args_dict):
    """Wrapper function to call 'call_amd_agent' with unpacked arguments."""
    call_amd_agent(
        domain=args_dict["domain"],
        src_username=args_dict["src_username"],
        src_password=args_dict["src_password"],
        dst_username=args_dict["dst_username"],
        playback_filename=args_dict["playback_filename"],
    )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--domain", type=str, default="192.168.1.124")
    parser.add_argument("--src-user-start", type=int, default=7401)
    parser.add_argument("--number-of-calls", type=int, default=1)
    parser.add_argument("--dst-num-start", type=int, default=8501)
    parser.add_argument("--playback-folder", type=str, default="wavs")
    args = parser.parse_args()
    playbacks_path = Path(args.playback_folder)
    playbacks_files = list(playbacks_path.glob("*.wav"))

    # processes
    processes = []
    for i in range(args.number_of_calls):
        src_user = args.src_user_start + i
        dst_num = args.dst_num_start + i
        playback_file = str(random.choice(playbacks_files))
        print(f"Calling {dst_num} from {src_user} with playback file {playback_file}")
        args_dict = {
            "domain": args.domain,
            "src_username": str(src_user),
            "src_password": "pass" + str(src_user),
            "dst_username": str(dst_num),
            "playback_filename": playback_file,
        }
        p = multiprocessing.Process(
            target=call_amd_agent_wrapper,
            args=(args_dict,),
        )
        processes.append(p)

    # Start all processes
    for p in processes:
        p.start()

    # Wait for all processes to finish
    for p in processes:
        p.join()
