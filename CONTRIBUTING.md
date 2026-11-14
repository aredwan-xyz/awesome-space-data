# Contributing

Thanks for helping keep this list useful.

## Add or fix a resource

1. Edit [`resources.tsv`](resources.tsv). Do not edit `README.md`'s list, `resources.json`,
   `resources.csv` or `index.html`; they are generated.
2. Add one line with seven fields separated by `|`:

   ```
   domain | kind | access | terms | name | url | description
   ```

   Example:

   ```
   Earth observation|API|Open||NASA POWER API|https://power.larc.nasa.gov/docs/services/api/|Daily weather and solar values for any point on Earth, back decades.
   ```

3. Check it builds:

   ```bash
   python3 build.py --no-check
   ```

4. Open a pull request with the change to `resources.tsv`. You can leave the generated
   files out; they are rebuilt after merge.

## Field rules

| Field | Rule |
|---|---|
| `domain` | One of the section names in the README. Propose a new one in an issue first. |
| `kind` | What it is: `API`, `Data`, `Archive`, `Catalogue`, `Viewer`, `Tool`, `Library`, `Framework`, `Media`, `Learning`, `Reference`, and so on. Reuse an existing value where one fits. |
| `access` | `Open`, `Free key`, `Free account`, `Free tier`, `Paid`, `Varies` or `See site`. |
| `terms` | Optional short note on reuse limits, if you know them. Leave blank if unsure. |
| `name` | The resource's own name. No marketing words. |
| `url` | The most direct working link. No tracking parameters. |
| `description` | One line saying what someone can do with it. No `|` character. |

## What belongs here

- It is useful for building something with space or Earth-observation data.
- It is reachable by the public (free, or paid with a clear public offer).
- The link works today.
- It is not already listed. The build fails on duplicate links.

What does not belong: news articles, single blog posts, paywalled papers, products with
no public access, and anything you are promoting without saying so.

If you are adding your own project or company, say so in the pull request.

## Report a dead link

Open an issue with the resource name and, if you can find it, the new address.
