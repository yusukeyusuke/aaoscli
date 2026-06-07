# aaos cli

AAOS/AOSP ワークツリー作業を補助する CLI です。

## Install for development

```sh
python3 -m pip install -e .
```

## Commands

```sh
aaos repo install
aaos repo tags
aaos repo branches
```

### Install repo

`repo` コマンドを指定ディレクトリに導入します。デフォルトは `~/.local/bin/repo` です。

```sh
aaos repo install
aaos repo install --bin-dir ~/bin
aaos repo install --force
```

### List manifest tags

```sh
aaos repo tags
aaos repo tags --limit 20
aaos repo tags --filter android-15
```

### List manifest branches

```sh
aaos repo branches
aaos repo branches --limit 20
aaos repo branches --filter android
```

