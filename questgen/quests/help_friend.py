# coding: utf-8
import itertools

from questgen.quests.base_quest import QuestBetween2, ROLES, RESULTS
from questgen import facts
from questgen import logic


class HelpFriend(QuestBetween2):
    TYPE = 'help_friend'
    TAGS = ('can_start', 'has_subquests')

    @classmethod
    def get_friend(cls, selector):
        return selector._kb[selector.preferences_friend().person]

    @classmethod
    def construct_from_place(cls, nesting, selector, start_place):

        friend = cls.get_friend(selector)

        return cls.construct(nesting=nesting,
                             selector=selector,
                             initiator=None,
                             initiator_position=start_place,
                             receiver=selector.new_person(first_initiator=False, candidates=(friend.uid, )),
                             receiver_position=selector.place_for(objects=(friend.uid,)))

    @classmethod
    def construct(cls, nesting, selector, initiator, initiator_position, receiver, receiver_position):

        hero = selector.heroes()[0]

        ns = selector._kb.get_next_ns()

        start = facts.Start(uid=ns+'start',
                            type=cls.TYPE,
                            nesting=nesting,
                            description=u'Начало: навестить соратника',
                            require=[facts.LocatedIn(object=hero.uid, place=initiator_position.uid)],
                            actions=[facts.Message(type='intro')])

        participants = [facts.QuestParticipant(start=start.uid, participant=receiver.uid, role=ROLES.RECEIVER) ]

        meeting = facts.State(uid=ns+'meeting',
                              description=u'встреча с соратником',
                              require=[facts.LocatedIn(object=hero.uid, place=receiver_position.uid)])

        finish_meeting = facts.Finish(uid=ns+'finish_meeting',
                                      result=RESULTS.SUCCESSED,
                                      nesting=nesting,
                                      description=u'соратнику оказана помощь',
                                      require=[facts.LocatedIn(object=hero.uid, place=receiver_position.uid)],
                                      actions=[facts.GiveReward(object=hero.uid, type='finish_meeting'),
                                               facts.GivePower(object=receiver.uid, power=1)])

        help_quest = selector.create_quest_from_person(nesting=nesting+1, initiator=receiver, tags=('can_continue',))
        help_extra = []

        for help_fact in logic.filter_subquest(help_quest, nesting):
            if isinstance(help_fact, facts.Start):
                help_extra.append(facts.Jump(state_from=meeting.uid, state_to=help_fact.uid, start_actions=[facts.Message(type='before_help')]))
            elif isinstance(help_fact, facts.Finish):
                if help_fact.result == RESULTS.SUCCESSED:
                    help_extra.append(facts.Jump(state_from=help_fact.uid, state_to=finish_meeting.uid, start_actions=[facts.Message(type='after_help')]))

        subquest = facts.SubQuest(uid=ns+'help_subquest', members=logic.get_subquest_members(itertools.chain(help_quest, help_extra)))

        line = [ start,

                 facts.Jump(state_from=start.uid, state_to=meeting.uid),

                 meeting,

                 finish_meeting,

                 subquest
                ]

        line.extend(participants)
        line.extend(help_quest)
        line.extend(help_extra)

        return line