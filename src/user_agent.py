# The main code: launching an user agent

import time
from argparse import ArgumentParser

import pjsua2 as pj

from config import UserAgent
from custom_callbacks import Account
from detection_algorithm import detect_answering_machine
from utils import (
    add_call_log_to_database,
    call_api,
    get_logger,
    get_number,
    store_metadata,
    store_wav,
)


def run_user_agent(
    domain,
    bot_username,
    bot_password,
    amd_dst,
    non_amd_dst,
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
    ep_cfg.logConfig.level = 0
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
    last_registration_time = time.time()
    while acc._call is None:
        time.sleep(0.01)
        # renewal condition
        if time.time() - last_registration_time > UserAgent.renew_time:
            last_registration_time = time.time()
            logger.info("Renew Registration...")
            acc.setRegistration(True)
    call = acc._call
    acc._call = None
    logger.info("Incoming call detected!")

    # wait for call to be confirmed
    start_time_for_call_confirmation = time.time()
    while (
        call.getInfo().state != pj.PJSIP_INV_STATE_CONFIRMED
        and time.time() - start_time_for_call_confirmation < UserAgent.max_inv_confirmed
    ):
        time.sleep(0.01)
    logger.info("Call confirmed!")
    logger.info(call.getInfo().remoteUri)
    logger.info(call.getInfo().remoteContact)

    # wait until media is consented
    start_time_for_media_consent = time.time()
    while (
        call.hasMedia() is False
        and time.time() - start_time_for_media_consent < UserAgent.max_media_consent
    ):
        time.sleep(0.1)
    logger.info("Media consented!")
    call_id = call.getInfo().callIdString
    logger.info(f"{call_id = }")

    # run AM detection algorithm
    logger.info("Running AMD algorithm...")
    try:
        metadata_dict = detect_answering_machine(call)
    except Exception as E:
        logger.info("exception at navigate_dialogue " * 10)
        logger.info(E)
        metadata_dict = {
            "call_id": call_id,
            "dialed_number": get_number(call.getInfo().remoteUri),
            "result": "exception",
            "duration": 0,
        }

    # make decision based on the result of the algorithm
    call_op_param = pj.CallOpParam(True)
    match metadata_dict["result"]:
        case "AMD":
            call.xfer(f"sip:{amd_dst}@{domain}", call_op_param)
        case "non-AMD":
            call.xfer(f"sip:{non_amd_dst}@{domain}", call_op_param)
        case _:
            call.hangup(call_op_param)

    # store call and metadata
    logger.info("Storing call and metadata...")
    store_wav(metadata_dict["call_id"] + ".wav")
    store_metadata(metadata_dict)
    add_call_log_to_database(metadata_dict)
    call_api()

    # close the things out
    start_time_to_delete_call = time.time()
    call.hangup(call_op_param)
    while call._delete_call is False and time.time() - start_time_to_delete_call < 1:
        time.sleep(0.01)
    del call
    logger.info("Call finished!")
    logger.info(metadata_dict)
    logger.info("deleting params...")
    # Destroy the library
    try:
        ep.libDestroy()
    except pj.Error:
        pass
    return metadata_dict
    logger.info("Agent finished!")
    logger.info("*" * 100)


if __name__ == "__main__":
    logger = get_logger()
    # UA_ENV="pc" python awaiting_user_agent.py
    parser = ArgumentParser()
    parser.add_argument("--domain", type=str, default="192.168.1.124")
    parser.add_argument("--src-user", type=str, default="8501")
    parser.add_argument("--src-pass", type=str, default="pass8501")
    parser.add_argument("--amd-dst", type=str, default="7600")
    parser.add_argument("--non-amd-dst", type=str, default="7601")
    parser.add_argument("--always", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            run_user_agent(
                domain=args.domain,
                bot_username=args.src_user,
                bot_password=args.src_pass,
                amd_dst=args.amd_dst,
                non_amd_dst=args.non_amd_dst,
            )
        except Exception as E:
            logger.info("exception at run_user_agent")
            logger.info(E)
        finally:
            if not args.always:
                break
