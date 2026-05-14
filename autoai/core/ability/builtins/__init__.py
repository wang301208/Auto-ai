from autoai.core.ability.builtins.create_new_ability import CreateNewAbility
from autoai.core.ability.builtins.query_language_model import QueryLanguageModel

BUILTIN_ABILITIES = {
    QueryLanguageModel.name(): QueryLanguageModel,
}
