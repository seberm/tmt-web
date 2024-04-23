import os
import tmt
import logging
from src.utils import git_handler as utils
from src.generators import json_generator, html_generator as html
from src.generators import yaml_generator
from celery.app import Celery

logger = tmt.Logger(logging.Logger("tmt-logger"))

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

app = Celery(__name__, broker=redis_url, backend=redis_url)


def get_tree(url: str, name: str, ref: str) -> tmt.base.Tree:
    """
    This function clones the repository and returns the Tree object
    :param ref: Object ref
    :param name: Object name
    :param url: Object url
    :return:
    """
    logger.print("Cloning the repository for url: " + url)
    logger.print("Parsing the url and name...")
    logger.print("URL: " + url)
    logger.print("Name: " + name)

    path = utils.get_git_repository(url, logger, ref)

    logger.print("Looking for tree...")
    tree = tmt.base.Tree(path=path, logger=logger)
    logger.print("Tree found!", color="green")
    return tree


def process_test_request(test_url: str, test_name: str, test_ref: str, return_object: bool, out_format: str) -> str | None | tmt.Test:
    """
    This function processes the request for a test and returns the HTML file or the Test object
    :param test_url: Test url
    :param test_name: Test name
    :param test_ref: Test repo ref
    :param return_object: Specify if the function should return the HTML file or the Test object
    :param out_format: Specifies output format
    :return:
    """

    tree = get_tree(test_url, test_name, test_ref)

    logger.print("Looking for the wanted test...")

    test_list = tree.tests()
    wanted_test = None
    # Find the desired Test object
    for test in test_list:
        if test.name == test_name:
            wanted_test = test
            break
    if wanted_test is None:
        logger.print("Test not found!", color="red")
        return None
    logger.print("Test found!", color="green")
    if not return_object:
        return wanted_test
    match out_format:
        case "html":
            return html.generate_test_html_page(wanted_test, logger=logger)
        case "json":
            return json_generator.generate_test_json(wanted_test, logger=logger)
        case "yaml":
            return yaml_generator.generate_test_yaml(wanted_test, logger=logger)


def process_plan_request(plan_url: str, plan_name: str, plan_ref: str, return_object: bool, out_format: str) -> str | None | tmt.Plan:
    """
    This function processes the request for a plan and returns the HTML file or the Plan object
    :param plan_url: Plan URL
    :param plan_name: Plan name
    :param plan_ref: Plan repo ref
    :param return_object: Specify if the function should return the HTML file or the Plan object
    :param out_format: Specifies output format
    :return:
    """

    tree = get_tree(plan_url, plan_name, plan_ref)

    logger.print("Looking for the wanted plan...")

    plan_list = tree.plans()
    wanted_plan = None
    # Find the desired Plan object
    for plan in plan_list:
        if plan.name == plan_name:
            wanted_plan = plan
            break
    if wanted_plan is None:
        logger.print("Plan not found!", color="red")
        return None
    logger.print("Plan found!", color="green")
    if not return_object:
        return wanted_plan
    match out_format:
        case "html":
            return html.generate_plan_html_page(wanted_plan, logger=logger)
        case "json":
            return json_generator.generate_plan_json(wanted_plan, logger=logger)
        case "yaml":
            return yaml_generator.generate_plan_yaml(wanted_plan, logger=logger)


def process_testplan_request(test_url, test_name, test_ref, plan_url, plan_name, plan_ref, out_format) -> str | None:
    """
    This function processes the request for a test and a plan and returns the HTML file
    :param test_url: Test URL
    :param test_name: Test name
    :param test_ref: Test repo ref
    :param plan_url: Plan URL
    :param plan_name: Plan name
    :param plan_ref: Plan repo ref
    :param out_format: Specifies output format
    :return:
    """
    test = process_test_request(test_url, test_name, test_ref, False, out_format)
    plan = process_plan_request(plan_url, plan_name, plan_ref, False, out_format)
    match out_format:
        case "html":
            return html.generate_testplan_html_page(test, plan, logger=logger)
        case "json":
            return json_generator.generate_testplan_json(test, plan, logger=logger)
        case "yaml":
            return yaml_generator.generate_testplan_yaml(test, plan, logger=logger)


@app.task
def main(test_url: str | None,
         test_name: str | None,
         test_ref: str | None,
         plan_url: str | None,
         plan_name: str | None,
         plan_ref: str | None,
         out_format: str | None) -> str | None:
    logger.print("Starting...", color="blue")
    if test_name is not None and plan_name is None:
        return process_test_request(test_url, test_name, test_ref, True, out_format)
    elif plan_name is not None and test_name is None:
        return process_plan_request(plan_url, plan_name, plan_ref, True, out_format)
    elif plan_name is not None and test_name is not None:
        return process_testplan_request(test_url, test_name, test_ref, plan_url, plan_name, plan_ref, out_format)


if __name__ == "__main__":
    print("This is not executable file!")