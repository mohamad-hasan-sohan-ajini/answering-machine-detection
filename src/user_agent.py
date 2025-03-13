# The main code: launching an user agent

import time
from argparse import ArgumentParser

import pjsua2 as pj

from config import UserAgent
from custom_callbacks import Account
from utils import (
    add_call_log_to_database,
    call_api,
    detect_answering_machine,
    delete_pj_obj_safely,
    get_logger,
    store_wav,
    store_metadata,
)


def run_user_agent(
    domain,
    bot_username,
    bot_password,
    operator_username,
):
    """Run the user agent."""
    # Log initial of the agent
    logger = get_logger()
    logger.info(f"Creating agent {bot_username}...")

    # Create and initialize the library
    ep = pj.Endpoint()
    ep.libCreate()

    # configure endpoint
    ep_cfg = pj.EpConfig()
    ep_cfg.logConfig.level = UserAgent.log_level
    ep.libInit(ep_cfg)
    ep.audDevManager().setNullDev()

    # configure endpoint transport
    sipTpConfig = pj.TransportConfig()
    ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sipTpConfig)

    # Start the library
    ep.libStart()

    # create account config
    acfg = pj.AccountConfig()
    acfg.idUri = f"sip:{bot_username}@{domain}"
    acfg.regConfig.registrarUri = f"sip:{domain}"

    # create authentication config
    cred = pj.AuthCredInfo("digest", "*", bot_username, 0, bot_password)
    acfg.sipConfig.authCreds.append(cred)

    # Create the account
    acc = Account()
    acc.create(acfg)

    # wait for a call
    t0 = time.time()
    while acc._call is None:
        time.sleep(0.01)
        # renewal condition
        if time.time() - t0 > UserAgent.renew_time:
            t0 = time.time()
            logger.info("Renew Registration...")
            acc.setRegistration(True)
    call = acc._call
    call_op_param = acc._call_op_param
    call_info = call.getInfo()

    # pj.PJSIP_INV_STATE_CALLING = 1
    # pj.PJSIP_INV_STATE_INCOMING = 2
    # pj.PJSIP_INV_STATE_EARLY = 3
    # pj.PJSIP_INV_STATE_CONNECTING = 4
    # pj.PJSIP_INV_STATE_CONFIRMED = 5
    t0 = time.time()
    while (
        call_info.state != pj.PJSIP_INV_STATE_CONFIRMED
        and time.time() - t0 < UserAgent.max_inv_confirmed
    ):
        print(call_info.state, call_info.stateText)
        time.sleep(0.01)
    for i in range(10):
        print(call.getInfo().remoteUri)
        print(call.getInfo().remoteContact)
        print("-" * 20)
    # wait until media is consented
    t0 = time.time()
    while time.time() - t0 < UserAgent.max_media_consent:
        if call.media_changed:
            call.getInfo()
            break
        time.sleep(0.1)
    call_id = call.getInfo().callIdString
    logger.info(f"{call_id = }")
    try:
        metadata_dict = detect_answering_machine(call)
    except Exception as E:
        logger.info("exception at navigate_dialogue " * 10)
        logger.info(E)
        metadata_dict = {
            "call_id": call_id,
            "result": "exception",
            "duration": 0,
        }
    match metadata_dict["result"]:
        case "AMD":
            call.xfer(f"sip:{operator_username}@{domain}", call_op_param)
        case "non-AMD":
            call.hangup(call_op_param)
        case _:
            call.hangup(call_op_param)
    # store audio and metadata in object storage
    store_wav(metadata_dict["call_id"] + ".wav")
    store_metadata(metadata_dict["call_id"] + ".json", metadata_dict)
    # log meta date in database
    add_call_log_to_database(metadata_dict)
    # also call proper callback API
    call_api(metadata_dict)
    # close the things out
    print(metadata_dict)
    print("deleting params...")
    print("*" * 100)
    delete_pj_obj_safely(call)
    delete_pj_obj_safely(call_op_param)
    delete_pj_obj_safely(acc)
    # Destroy the library
    try:
        ep.libDestroy()
    except pj.Error:
        pass
    return metadata_dict


if __name__ == "__main__":
    logger = get_logger()
    # UA_ENV="pc" python awaiting_user_agent.py
    parser = ArgumentParser()
    parser.add_argument("--domain", type=str, default="192.168.1.124")
    parser.add_argument("--src-user", type=str, default="8501")
    parser.add_argument("--src-pass", type=str, default="pass8501")
    parser.add_argument("--dst-num", type=str, default="7600")
    parser.add_argument("--always", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            run_user_agent(
                domain=args.domain,
                bot_username=args.src_user,
                bot_password=args.src_pass,
                operator_username=args.dst_num,
            )
        except Exception as E:
            logger.info("exception at run_user_agent")
            logger.info(E)
        finally:
            if not args.always:
                break
