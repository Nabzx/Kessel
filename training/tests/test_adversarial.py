from kessel_training.adversarial import run_suite


def test_reward_and_reset_exploits_have_no_unearned_task_credit():
    report = run_suite()
    assert report["passed"]
    assert report["cases"]["saturated_joint_stuck"]["reason"] == "stuck"
    assert report["cases"]["wall_push"]["repeated_step_rejected"]
    assert report["cases"]["out_of_zone_tipping"]["delivered_kg"] == 0
