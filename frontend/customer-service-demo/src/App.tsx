import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import ChatInputForm from "./components/chat-input-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { cn } from "./lib/utils";

interface IConversation {
  id: string;
  from: "user" | "assistant";
  output: string;
  session_completed: boolean;
}

interface IStartChatResponse {
  session_id: string;
  response: string;
  output: string;
}

interface IContinueChatResponse {
  output: string;
  session_completed: boolean;
  session_id: string;
  ticket_id?: string;
}

interface IErrorResponse {
  message: string;
  output: string;
  session_id: string;
  session_completed: boolean;
}

function App() {
  const [conversations, setConversations] = useState<IConversation[]>([]);

  const chatBoxRef = useRef<HTMLDivElement>(null);

  const addMessageToConversation = useCallback((message: IConversation) => {
    setConversations((prev) => [...prev, message]);
  }, []);

  const startChatMutation = useMutation({
    mutationFn: async (payload: { question: string }) => {
      const response = await fetch("http://localhost:8000/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: payload.question }),
      });
      if (!response.ok) {
        // return error response
        const errorData = (await response.json()) as IErrorResponse;
        throw errorData;
      }
      return response.json() as Promise<IStartChatResponse>;
    },
    onSuccess: (data) => {
      addMessageToConversation({
        id: crypto.randomUUID(),
        from: "assistant",
        output: data.output,
        session_completed: false,
      });
    },
  });

  const continueChatMutation = useMutation({
    mutationFn: async (payload: { question: string; session_id: string }) => {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: payload.question,
          session_id: payload.session_id,
        }),
      });
      if (!response.ok) {
        const errorData = (await response.json()) as IErrorResponse;
        throw errorData;
      }
      return response.json() as Promise<IContinueChatResponse>;
    },
    onSuccess: (data) => {
      addMessageToConversation({
        id: crypto.randomUUID(),
        from: "assistant",
        output: data.output,
        session_completed: data.session_completed,
      });
    },
  });

  useEffect(() => {
    if (conversations.length > 0) {
      chatBoxRef.current?.scrollTo({
        top: chatBoxRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [conversations]);

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center">
      <Card className="w-md">
        <CardHeader>
          <CardTitle>Customer Support AI</CardTitle>
          <CardDescription>
            Ask any questions you have about our product
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            ref={chatBoxRef}
            className="flex flex-col gap-4 h-96 overflow-y-auto"
          >
            {conversations.map((item) => (
              <div
                key={item.id}
                className={cn(
                  "flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm",
                  item.from === "assistant"
                    ? "bg-muted"
                    : "bg-primary text-primary-foreground ml-auto"
                )}
              >
                <Markdown>{item.output}</Markdown>
              </div>
            ))}
            {startChatMutation.isPending || continueChatMutation.isPending ? (
              <div className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm bg-muted">
                <span className="italic text-muted-foreground">
                  Customer Support AI is typing...
                </span>
              </div>
            ) : null}
          </div>
        </CardContent>
        <CardFooter>
          <ChatInputForm
            isEmpty={conversations.length === 0}
            isLoading={
              startChatMutation.isPending || continueChatMutation.isPending
            }
            onSubmit={(message) => {
              addMessageToConversation({
                id: crypto.randomUUID(),
                from: "user",
                output: message,
                session_completed: false,
              });

              if (conversations.length === 0) {
                startChatMutation.mutate({
                  question: message,
                });
              } else {
                if (startChatMutation.isSuccess) {
                  continueChatMutation.mutate({
                    question: message,
                    session_id: startChatMutation.data.session_id,
                  });
                }
              }
            }}
          />
        </CardFooter>
      </Card>
    </main>
  );
}

export default App;
