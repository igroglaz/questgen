# coding: utf-8

import random

from questgen import facts
from questgen import exceptions


def activate_events(knowledge_base):
    choosen_facts = []
    removed_facts = []

    events = list(knowledge_base.filter(facts.Event))

    # validate events
    events_tags = set(event.uid for event in events)
    for fact in knowledge_base.facts():
        if  len(events_tags & set(fact.tags)) > 1:
            raise exceptions.MoreThenOneEventTagError(fact=fact)

    # chose events
    for event in events:
        event_facts = filter(lambda fact: event.uid in fact.tags, knowledge_base.facts())

        if not event_facts:
            raise exceptions.NoTaggedEventMembersError(event=event)

        choosen_facts.append(random.choice(event_facts))
        removed_facts.extend(event_facts)

    knowledge_base -= set(removed_facts) - set(choosen_facts)


def determine_default_choices(knowledge_base):
    processed_choices = set()
    linked_options = {}

    for link in knowledge_base.filter(facts.OptionsLink):
        for option_uid in link.options:
            if option_uid in linked_options:
                raise exceptions.OptionWithTwoLinksError(option=knowledge_base[option_uid])
            linked_options[option_uid] = link

    for choice in knowledge_base.filter(facts.Choice):
        if choice.uid in processed_choices:
            continue

        processed_choices.add(choice.uid)

        options_choices = [option for option in knowledge_base.filter(facts.Option) if option.state_from == choice.uid]
        default_option = random.choice(options_choices)

        if default_option.uid in linked_options:
            for linked_option_uid in linked_options[default_option.uid].options:
                if linked_option_uid == default_option.uid:
                    continue

                linked_choice_uid = knowledge_base[linked_option_uid].state_from

                if linked_choice_uid in processed_choices:
                    raise exceptions.LinkedOptionWithProcessedChoiceError(option=knowledge_base[linked_option_uid])

                processed_choices.add(linked_choice_uid)

                knowledge_base += facts.ChoicePath(choice=linked_choice_uid, option=linked_option_uid, default=True)

        knowledge_base += facts.ChoicePath(choice=choice.uid, option=default_option.uid, default=True)


def change_choice(knowledge_base, choice_uid, new_option_uid, default):

    old_path = (path for path in knowledge_base.filter(facts.ChoicePath) if path.choice == choice_uid).next()

    knowledge_base -= old_path
    knowledge_base += facts.ChoicePath(choice=choice_uid, option=new_option_uid, default=default)

    links = [link for link in knowledge_base.filter(facts.OptionsLink) if new_option_uid in link.options]
    if links:
        link = links[0]
        for linked_option_uid in link.options:
            if new_option_uid == linked_option_uid:
                continue
            linked_choice_uid = knowledge_base[linked_option_uid].state_from
            old_path = (path for path in knowledge_base.filter(facts.ChoicePath) if path.choice == linked_choice_uid).next()

            knowledge_base -= old_path
            knowledge_base += facts.ChoicePath(choice=linked_choice_uid, option=linked_option_uid, default=default)

    return True


def remove_broken_states(knowledge_base):

    while True:
        states_to_remove = []

        for state in knowledge_base.filter(facts.State):
            if isinstance(state, facts.Start):
                pass
            elif not filter(lambda jump: jump.state_to == state.uid, knowledge_base.filter(facts.Jump)):
                states_to_remove.append(state)
            elif isinstance(state, facts.Finish):
                pass
            elif not filter(lambda jump: jump.state_from == state.uid, knowledge_base.filter(facts.Jump)):
                states_to_remove.append(state)

        knowledge_base -= states_to_remove

        jumps_to_remove = []

        for jump in knowledge_base.filter(facts.Jump):
            if (jump.state_from not in knowledge_base or
                jump.state_to not in knowledge_base):
                jumps_to_remove.append(jump)

        knowledge_base -= jumps_to_remove

        if not states_to_remove and not jumps_to_remove:
            break


def remove_restricted_states(knowledge_base):

    states_to_remove = set()

    for restriction_fact in knowledge_base.filter(facts.OnlyGoodBranches):
        for state in knowledge_base.filter(facts.State):
            for action in state.actions:
                if isinstance(action, facts.GivePower):
                    if action.person == restriction_fact.person and action.power < 0:
                        states_to_remove.add(state)

    for restriction_fact in knowledge_base.filter(facts.OnlyBadBranches):
        for state in knowledge_base.filter(facts.State):
            for action in state.actions:
                if isinstance(action, facts.GivePower):
                    if action.person == restriction_fact.person and action.power > 0:
                        states_to_remove.add(state)

    knowledge_base -= states_to_remove