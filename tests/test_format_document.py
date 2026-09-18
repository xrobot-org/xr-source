from xr_source.format import Group, Indent, concat, join, line, render, softline


def call_doc(arguments):
    return Group(
        concat(
            "foo(",
            Indent(concat(softline, join(concat(",", line), arguments))),
            softline,
            ")",
        )
    )


def test_group_stays_flat_when_it_fits() -> None:
    assert render(call_doc(["a", "b"]), width=80) == "foo(a, b)"


def test_group_breaks_when_needed() -> None:
    assert render(
        call_doc(["long_argument_a", "long_argument_b"]),
        width=20,
    ) == (
        "foo(\n"
        "  long_argument_a,\n"
        "  long_argument_b\n"
        ")"
    )
