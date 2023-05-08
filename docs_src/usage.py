# -*- coding: utf-8 -*-
# Tanjun Examples - A collection of examples for Tanjun.
# Written in 2023 by Faster Speeding Lucina@lmbyrne.dev
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain worldwide.
# This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software.
# If not, see <https://creativecommons.org/publicdomain/zero/1.0/>.

# pyright: reportUnusedFunction=none
# pyright: reportUnusedVariable=none

import typing

import aiohttp
import alluka
import hikari

import tanjun
from tanjun import annotations


def gateway_bot_example() -> None:
    bot = hikari.impl.GatewayBot("TOKEN")
    client = tanjun.Client.from_gateway_bot(bot, declare_global_commands=True, mention_prefix=True)

    ...

    bot.run()


def rest_bot_example() -> None:
    bot = hikari.impl.RESTBot("TOKEN", hikari.TokenType.BOT)
    tanjun.Client.from_rest_bot(bot, bot_managed=True, declare_global_commands=True)
    bot.run()


def client_lifetime_example(bot: hikari.GatewayBotAware) -> None:
    client = tanjun.Client.from_gateway_bot(bot)

    @client.with_client_callback(tanjun.ClientCallbackNames.STARTING)
    async def on_starting(client: alluka.Injected[tanjun.abc.Client]) -> None:
        client.set_type_dependency(aiohttp.ClientSession, aiohttp.ClientSession())

    async def on_closed(session: alluka.Injected[aiohttp.ClientSession]) -> None:
        await session.close()

    client.add_client_callback(tanjun.ClientCallbackNames.CLOSED, on_closed)


def components_example() -> None:
    component = tanjun.Component()

    @component.with_command
    @tanjun.as_slash_command("name", "description")
    async def slash_command(ctx: tanjun.abc.SlashContext) -> None:
        ...

    @component.with_listener()
    async def event_listener(event: hikari.Event) -> None:
        ...


def load_from_scope_example() -> None:
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.MessageContext) -> None:
        ...

    component = tanjun.Component().load_from_scope()


def as_loader_example() -> None:
    component = tanjun.Component().load_from_scope()

    @tanjun.as_loader
    def load(client: tanjun.Client) -> None:
        client.add_component(component)

    @tanjun.as_unloader
    def unload(client: tanjun.Client) -> None:
        client.remove_component(component)


def make_loader_example() -> None:
    component = tanjun.Component().load_from_scope()

    loader = component.make_loader()


def loading_example(bot: hikari.GatewayBotAware) -> None:
    (
        tanjun.Client.from_gateway_bot(bot)
        .load_directory("./bot/components", namespace="bot.components")
        .load_modules("bot.owner")
    )


def slash_command_example() -> None:
    @tanjun.with_str_slash_option("option", "description")
    @tanjun.as_slash_command("name", "description")
    async def slash_command(ctx: tanjun.abc.SlashContext) -> None:
        ...


def slash_command_group_example() -> None:
    ding_group = tanjun.slash_command_group("ding", "ding group")

    @ding_group.as_sub_command("dong", "dong command")
    async def dong_command(ctx: tanjun.abc.SlashContext) -> None:
        ...

    ding_ding_group = ding_group.make_sub_group("ding", "ding ding group")

    @ding_ding_group.as_sub_command("ding", "ding ding ding command")
    async def ding_command(ctx: tanjun.abc.SlashContext) -> None:
        ...


def message_command_example(bot: hikari.GatewayBotAware) -> None:
    tanjun.Client.from_gateway_bot(bot).add_prefix("!")

    ...

    @tanjun.with_option("reason", "--reason", "-r", default=None)  # This can be triggered as --reason or -r
    @tanjun.with_multi_option("users", "--user", "-u", default=None)  # This can be triggered as --user or -u
    @tanjun.with_greedy_argument("content")
    @tanjun.with_argument("days", converters=int)
    @tanjun.as_message_command("meow command", "description")
    async def message_command(ctx: tanjun.abc.MessageContext) -> None:
        ...


def message_command_group_example() -> None:
    # prefixes=["!"]

    @tanjun.as_message_command_group("groupy")
    async def groupy_group(ctx: tanjun.abc.MessageContext):
        ...

    @groupy_group.as_sub_command("sus drink")
    async def sus_drink_command(ctx: tanjun.abc.MessageContext):
        ...

    @groupy_group.as_sub_group("tour")
    async def tour_group(ctx: tanjun.abc.MessageContext):
        ...

    @tour_group.as_sub_command("de france")
    async def de_france_command(ctx: tanjun.abc.MessageContext):
        ...


def context_menu_example(component: tanjun.Component) -> None:
    @component.with_command
    @tanjun.as_message_menu("name")
    async def message_menu_command(ctx: tanjun.abc.MenuContext, message: hikari.Message) -> None:
        ...

    @component.with_command
    @tanjun.as_user_menu("name")
    async def user_menu_command(ctx: tanjun.abc.MenuContext, user: hikari.User) -> None:
        ...


class Video:
    ...


def get_video(value: str) -> Video:
    ...


# isort: off


def annotations_example() -> None:
    from typing import Annotated, Optional

    from tanjun.annotations import Bool, Converted, Int, Ranged, Str, User

    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        name: Annotated[Str, "description"],
        age: Annotated[Int, Ranged(13, 130), "an int option with a min, max of 13, 130"],
        video: Annotated[Video, Converted(get_video), "a required string option which is converted with get_video"],
        user: Annotated[Optional[User], "a user option which defaults to None"] = None,
        enabled: Annotated[Bool, "a bool option which defaults to True"] = True,
    ) -> None:
        ...


# isort: on


def wrapped_command_example() -> None:
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.with_guild_check(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context) -> None:
        ...


def responding_to_commands_example() -> None:
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    @tanjun.as_user_menu("name")
    async def command(
        ctx: tanjun.abc.Context, user: typing.Annotated[typing.Optional[annotations.User], "The user to target"] = None
    ) -> None:
        user = user or ctx.author
        message = await ctx.respond(
            "message content",
            attachments=[hikari.File("./its/a/mystery.jpeg")],
            embeds=[hikari.Embed(title=str(ctx.author)).set_thumbnail(ctx.author.display_avatar_url)],
            ensure_result=True,
        )


def ephemeral_response_example(component: tanjun.Component) -> None:
    # All this command's responses will be ephemeral.
    @component.with_command
    @tanjun.as_slash_command("name", "description", default_to_ephemeral=True)
    async def command_1(ctx: tanjun.abc.SlashContext) -> None:
        await ctx.respond("hello friend")

    @component.with_command
    @tanjun.as_user_menu("name")
    async def command_2(ctx: tanjun.abc.MenuContext, user: hikari.User) -> None:
        await ctx.create_initial_response("Starting the thing", ephemeral=True)  # private response
        await ctx.respond("meow")  # public response
        await ctx.create_followup("finished the thing", ephemeral=True)  # private response


def autocomplete_example(component: tanjun.Component) -> None:
    @component.with_command
    @tanjun.with_str_slash_option("opt1", "description")
    @tanjun.with_str_slash_option("opt2", "description", default=None)
    @tanjun.as_slash_command("name", "description")
    async def slash_command(ctx: tanjun.abc.SlashContext, opt1: str, opt2: typing.Optional[str]) -> None:
        ...

    @slash_command.with_str_autocomplete("opt1")
    async def opt1_autocomplete(ctx: tanjun.abc.AutocompleteContext, value: str) -> None:
        await ctx.set_choices((("name", "value"), ("other_name", "other_value")), other_other_name="other_other_value")

    async def opt2_autocomplete(ctx: tanjun.abc.AutocompleteContext, value: str) -> None:
        await ctx.set_choices({"name": "value", "other_name": "other_value"})

    slash_command.set_str_autocomplete("opt2", opt2_autocomplete)


class Foo:
    ...


class Bar:
    ...


def set_client_deps_example(bot: hikari.GatewayBotAware) -> None:
    client = tanjun.Client.from_gateway_bot(bot)
    client.set_type_dependency(Foo, Foo())
    client.set_type_dependency(Bar, Bar())


def require_deps() -> None:
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.SlashContext, foo_impl: alluka.Injected[Foo], bar_impl: Bar = alluka.inject(type=Bar)
    ) -> None:
        ...


def standard_check_example() -> None:
    @tanjun.with_guild_check(follow_wrapped=True)
    @tanjun.with_author_permission_check(hikari.Permissions.BAN_MEMBERS)
    @tanjun.with_own_permission_check(hikari.Permissions.BAN_MEMBERS, follow_wrapped=True)
    @tanjun.as_message_command("name")
    @tanjun.as_slash_command("name", "description", default_member_permissions=hikari.Permissions.BAN_MEMBERS)
    async def command(ctx: tanjun.abc.Context) -> None:
        ...


class DbResult:
    banned: bool = False


class Db:
    async def get_user(self, user: hikari.Snowflake) -> DbResult:
        raise NotImplementedError


def using_checks_example() -> None:
    component = (
        tanjun.Component()
        .add_check(tanjun.checks.GuildCheck())
        .add_check(tanjun.checks.AuthorPermissionCheck(hikari.Permissions.BAN_MEMBERS))
        .add_check(tanjun.checks.OwnPermissionCheck(hikari.Permissions.BAN_MEMBERS))
    )

    @component.with_check
    async def db_check(ctx: tanjun.abc.Context, db: alluka.Injected[Db]) -> bool:
        if (await db.get_user(ctx.author.id)).banned:
            raise tanjun.CommandError("You are banned from using this bot")

        return False

    @tanjun.with_owner_check(follow_wrapped=True)
    @tanjun.as_message_command("name")
    @tanjun.as_slash_command("name", "description")
    async def owner_only_command(ctx: tanjun.abc.Context):
        ...


def custom_check_example() -> None:
    def check(ctx: tanjun.abc.Context) -> bool:
        if ctx.author.discriminator % 2:
            raise tanjun.CommandError("You are not one of the chosen ones")

        return True


def pre_execution_hook_example() -> None:
    hooks = tanjun.AnyHooks()

    @hooks.with_pre_execution  # hooks.add_pre_execution
    async def pre_execution_hook(ctx: tanjun.abc.Context) -> None:
        ...


def post_execution_hook_example(hooks: tanjun.abc.AnyHooks) -> None:
    @hooks.with_post_execution  # hooks.add_post_execution
    async def post_execution_hook(ctx: tanjun.abc.Context) -> None:
        ...


def success_hook_example(hooks: tanjun.abc.AnyHooks) -> None:
    @hooks.with_on_success  # hooks.add_success_hook
    async def success_hook(ctx: tanjun.abc.Context) -> None:
        ...


def error_hook_example(hooks: tanjun.abc.AnyHooks) -> None:
    @hooks.with_on_error  # hooks.add_on_error
    async def error_hook(ctx: tanjun.abc.Context, error: Exception) -> typing.Optional[bool]:
        ...


def parser_error_hook_example(hooks: tanjun.abc.AnyHooks) -> None:
    @hooks.with_on_parser_error  # hooks.add_on_parser_error
    async def parser_error_hook(ctx: tanjun.abc.Context, error: tanjun.ParserError) -> None:
        ...


def concurrency_limiter_config_example(bot: hikari.GatewayBotAware) -> None:
    client = tanjun.Client.from_gateway_bot(bot)
    (
        tanjun.InMemoryConcurrencyLimiter()
        .set_bucket("main_commands", tanjun.BucketResource.USER, 2)
        .disable_bucket("plugin.meta")
        .add_to_client(client)
    )


def assign_concurrency_limit_example() -> None:
    @tanjun.with_concurrency_limit("main_commands", follow_wrapped=True)
    @tanjun.as_message_command("name")
    @tanjun.as_slash_command("name", "description")
    async def user_command(ctx: tanjun.abc.Context) -> None:
        ...


def cooldown_config_example(bot: hikari.GatewayBotAware) -> None:
    client = tanjun.Client.from_gateway_bot(bot)
    (
        tanjun.InMemoryCooldownManager()
        .set_bucket("main_commands", tanjun.BucketResource.USER, 5, 60)
        .disable_bucket("plugin.meta")
        .add_to_client(client)
    )


def assign_cooldown_example() -> None:
    @tanjun.with_cooldown("main_commands", follow_wrapped=True)
    @tanjun.as_message_command("name")
    @tanjun.as_slash_command("name", "description")
    async def user_command(ctx: tanjun.abc.Context) -> None:
        ...


def localisation_example() -> None:
    @tanjun.as_slash_command({hikari.Locale.EN_US: "Hola"}, "description")
    async def command(ctx: tanjun.abc.Context) -> None:
        ...


def client_localiser_example(bot: hikari.GatewayBotAware) -> None:
    client = tanjun.Client.from_gateway_bot(bot)

    (
        tanjun.dependencies.BasicLocaliser()
        .set_variants(
            "slash:command name:name", {hikari.Locale.EN_US: "american variant", hikari.Locale.EN_GB: "english variant"}
        )
        .set_variants(
            "message_menu:command name:check:tanjun.OwnerCheck",
            {hikari.Locale.JA: "konnichiwa", hikari.Locale.ES_ES: "Hola"},
        )
        .add_to_client(client)
    )


def response_localisation_example() -> None:
    LOCALISED_RESPONSES: dict[str, str] = {
        hikari.Locale.DA: "Hej",
        hikari.Locale.DE: "Hallo",
        hikari.Locale.EN_GB: "Good day fellow sir",
        hikari.Locale.EN_US: "*shoots you*",
        hikari.Locale.ES_ES: "Hola",
        hikari.Locale.FR: "Bonjour, camarade baguette",
        hikari.Locale.PL: "Musimy szerzyć gejostwo w Strefach wolnych od LGBT, musimy zrobić rajd gejowski",
        hikari.Locale.SV_SE: "Hej, jag älskar min Blåhaj",
        hikari.Locale.VI: "Xin chào, Cây nói tiếng Việt",
        hikari.Locale.TR: "Merhaba",
        hikari.Locale.CS: "Ahoj",
        hikari.Locale.ZH_CN: "自由香港",
        hikari.Locale.JA: "こんにちは、アニメの女の子だったらいいのに",
        hikari.Locale.ZH_TW: "让台湾自由",
    }

    @tanjun.as_slash_command("name", "description")
    async def as_slash_command(ctx: tanjun.abc.SlashContext) -> None:
        await ctx.respond(LOCALISED_RESPONSES.get(ctx.interaction.locale, "hello"))
