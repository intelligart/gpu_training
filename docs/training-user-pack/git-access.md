# 程式來源的 Git 存取

**送進平台的程式 repo 必須放在 [intelligart](https://github.com/intelligart) 組織底下**，
`repo_url` 一律是 `git@github.com:intelligart/<repo>.git`。個人帳號或其他組織的 repo，
包括官方開源專案（例如 `Lightricks/LTX-2`），都要先 fork 或搬到 intelligart 再使用。

平台只從 Git 取得程式：`submit_job` 給 `repo_url` 與完整 commit SHA，
MCP server 主機用**平台自己的 Git 權限** clone 該 commit，再交給 Slurm。
所以有兩邊都要讀得到 repo：

| 誰 | 用途 | 用誰的權限 |
|---|---|---|
| 你的機器 | clone、commit、push、取得完整 SHA | 你自己的 GitHub 帳號與 SSH key，帳號需是 intelligart 成員 |
| 平台（MCP server 主機） | 每次 submission 依 SHA 準備 source | 平台的 Git 身分，可讀 intelligart 的 repo |

[回使用者包](README.md) · [三分鐘快速開始](../mcp-quickstart.md) · [常見問題](../../MCP_GUIDE.md#常見問題與停止條件)

## 1. 把程式放進 intelligart

| 情況 | 做法 |
|---|---|
| 新專案 | 在 intelligart 底下建 private repo（例如 `intelligart/<project>-training`），push 程式 |
| 已在個人帳號或其他組織 | 請 intelligart 管理員建 repo，或 transfer 到 intelligart；也可在 intelligart 建新 repo 後 push 既有歷史 |
| 官方開源專案（如 LTX-2） | Fork 到 intelligart（例如 `intelligart/LTX-2`），用 fork 的 commit SHA 送 job，不直接指向 upstream |

搬移既有歷史到 intelligart 的新 repo：

```bash
cd <本機的 repo>
git remote add intelligart git@github.com:intelligart/<repo>.git
git push intelligart --all
git push intelligart --tags
```

建 repo、transfer 或 fork 需要 intelligart 的對應權限；沒有權限時找 intelligart 管理員，
不要改放到個人帳號。

## 2. 用自己的 SSH key

- 使用**自己的** GitHub 帳號與 key，不借用或複製別人的 private key；
  push 與 commit 會記在 key 所屬的帳號下。
- 帳號要先加入 intelligart 組織，並取得該 repo 的權限。
- Private key 只放在 `~/.ssh/`，不貼進聊天、不提交到 Git。
- 這是共用主機時，建議為這台另產生一把專用 key，加到自己的 GitHub 帳號，不用時直接刪除：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_github -C "<這台主機用途>"
cat ~/.ssh/id_ed25519_github.pub   # 貼到 GitHub → Settings → SSH and GPG keys
```

**權限必須是 `600`。** 從別處複製來的 key 常是 `664` 或 `777`，
SSH 會顯示 `WARNING: UNPROTECTED PRIVATE KEY FILE!` 並直接忽略這把 key：

```bash
chmod 600 ~/.ssh/id_ed25519_github
```

不能 `chmod` 別人擁有的檔案；檔案擁有者不是自己時，請擁有者處理，不要用 sudo 讀取他人的 key。

## 3. 同一台機器有多個 GitHub 帳號

在 `~/.ssh/config`（權限 `600`）為每個帳號設一個 host 別名，避免用錯 key：

```text
Host github-work
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
```

Clone 時用別名，並讓該 repo 固定用同一把 key：

```bash
git clone git@github-work:intelligart/<repo>.git
git -C <repo> config core.sshCommand "ssh -i ~/.ssh/id_ed25519_github -o IdentitiesOnly=yes"
```

別名只用在你自己的機器上。送 job 的 `repo_url` 仍寫標準格式
`git@github.com:intelligart/<repo>.git`，不要寫別名。

## 4. 驗證

```bash
ssh -T github-work
# 預期：Hi <你的帳號>! You've successfully authenticated, but GitHub does not provide shell access.

git ls-remote git@github-work:intelligart/<repo>.git | head -3
# 預期：列出 HEAD 與 branches
```

| 結果 | 意思 | 處理 |
|---|---|---|
| `Hi <帳號>!` 帳號不是你預期的 | 用到別把 key | 檢查 `~/.ssh/config` 與 `IdentitiesOnly yes` |
| `Permission denied (publickey)` | Key 沒加到 GitHub，或權限不是 `600` 被忽略 | 加 public key、`chmod 600` |
| `ERROR: Repository not found.` | 對 GitHub 來說**沒有權限等同不存在**；帳號不是 intelligart 成員，或沒有該 repo 權限 | 請 intelligart 管理員把你加入組織或該 repo，接受邀請後重試 |
| https 要求輸入帳號密碼 | Repo 不是公開的 | 改用 SSH URL；不要把 token 寫進 URL |

## 5. 確認平台讀得到

平台可讀取 intelligart 的 repo，但每個新 repo 第一次使用前仍要驗證：
送一個很小的 smoke job。平台讀不到時會在 source preparation 階段失敗，
不會配置 GPU；成功時回應的 `source_commit` 會等於你給的 SHA。
失敗時把 repo 名稱與錯誤交給 Operator 確認平台權限。

## 6. 送 job 前

```bash
git push origin <branch>
git rev-parse HEAD   # 完整 40 字元 SHA，填進 submit_job 的 branch
```

- `repo_url` 一定要填，而且是 `git@github.com:intelligart/<repo>.git`；
  留空時平台會改用預設的共用 checkout，不會報錯。
- 只會帶入已 push 的 commit，本機未 commit／未 push 的修改不在 job 裡。
- 接著依 [送 job 前檢查](../mcp-quickstart.md#送-job-前檢查) 與 [遷移資料卡](migration-card.md) 整理摘要。
